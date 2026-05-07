"""
Budget alert endpoints — set, read, delete daily cost budgets.
"""
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import ApiKeyContext, ensure_role, require_api_key_context
from api.costing import compute_request_cost
from api.license import require_feature_ctx
from api.schemas import BudgetAlertPayload, BudgetAlertResponse
from storage.database import get_session
from storage.models import AuditLog, BudgetAlert, Request

router = APIRouter(prefix="/alerts")


async def _get_spent_today(db: AsyncSession, api_key: str) -> float:
    day_start = time.time() - (time.time() % 86400)
    result = await db.execute(
        select(Request).where(Request.api_key == api_key, Request.timestamp >= day_start)
    )
    spent = 0.0
    for req in result.scalars().all():
        spent += compute_request_cost(req.model, req.metadata_ or {}, req.input, req.output)
    return round(spent, 6)


async def _audit(db: AsyncSession, action: str, detail: str) -> None:
    db.add(AuditLog(id=str(uuid.uuid4()), action=action, detail=detail, timestamp=time.time()))
    await db.commit()


@router.post("/budget")
async def set_budget(
    payload: BudgetAlertPayload,
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_feature_ctx("alerts")),
):
    ensure_role(ctx, "admin")
    result = await db.execute(select(BudgetAlert).where(BudgetAlert.id == "default"))
    alert = result.scalar_one_or_none()

    if alert:
        alert.daily_budget_usd = payload.daily_budget_usd
        # Preserve existing destinations when not explicitly provided.
        if payload.webhook_url is not None:
            alert.webhook_url = payload.webhook_url
        if payload.email is not None:
            alert.email = payload.email
        alert.triggered_today = False
    else:
        alert = BudgetAlert(
            id="default",
            daily_budget_usd=payload.daily_budget_usd,
            webhook_url=payload.webhook_url,
            email=payload.email,
        )
        db.add(alert)

    await db.commit()
    await _audit(db, "budget_alert_updated", f"by_role={ctx.role} budget={payload.daily_budget_usd}")

    spent = await _get_spent_today(db, ctx.key)
    return BudgetAlertResponse(
        daily_budget_usd=alert.daily_budget_usd,
        webhook_url=alert.webhook_url,
        email=alert.email,
        triggered_today=alert.triggered_today,
        spent_today_usd=spent,
        percent_used=round(spent / alert.daily_budget_usd * 100, 1) if alert.daily_budget_usd > 0 else 0,
    )


@router.get("/budget")
async def get_budget(
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_feature_ctx("alerts")),
):
    result = await db.execute(select(BudgetAlert).where(BudgetAlert.id == "default"))
    alert = result.scalar_one_or_none()

    if not alert:
        return {"configured": False}

    spent = await _get_spent_today(db, ctx.key)
    return BudgetAlertResponse(
        daily_budget_usd=alert.daily_budget_usd,
        webhook_url=alert.webhook_url,
        email=alert.email,
        triggered_today=alert.triggered_today,
        spent_today_usd=spent,
        percent_used=round(spent / alert.daily_budget_usd * 100, 1) if alert.daily_budget_usd > 0 else 0,
    )


@router.delete("/budget")
async def delete_budget(
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_feature_ctx("alerts")),
):
    ensure_role(ctx, "admin")
    result = await db.execute(select(BudgetAlert).where(BudgetAlert.id == "default"))
    alert = result.scalar_one_or_none()
    if alert:
        await db.delete(alert)
        await db.commit()
        await _audit(db, "budget_alert_deleted", f"by_role={ctx.role}")
    return {"deleted": True}
