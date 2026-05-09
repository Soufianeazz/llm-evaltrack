from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import ApiKeyContext, require_api_key_context
from api.customer_access import evaluate_customer_access
from storage.database import get_session
from storage.models import CustomerAccount

PLAN_ALIAS = {
    "demo": "enterprise",
    "pilot": "enterprise",
    "pilot14": "enterprise",
    "pilot_14": "enterprise",
    "full_pilot": "enterprise",
    "trial": "enterprise",
    "free": "free",
    "starter": "starter",
    "team": "team",
    "scale": "scale",
    "enterprise": "enterprise",
}

PLAN_FEATURES = {
    "free": {
        "basic_stats_24h": True,
        "prompt_debugger": False,
        "agent_debugger": False,
        "advanced_analytics": False,
        "compliance_gdpr": False,
        "private_deploy": False,
        "sla_security_package": False,
    },
    "starter": {
        "basic_stats_24h": True,
        "prompt_debugger": True,
        "agent_debugger": False,
        "advanced_analytics": False,
        "compliance_gdpr": False,
        "private_deploy": False,
        "sla_security_package": False,
    },
    "team": {
        "basic_stats_24h": True,
        "prompt_debugger": True,
        "agent_debugger": True,
        "advanced_analytics": True,
        "compliance_gdpr": False,
        "private_deploy": False,
        "sla_security_package": False,
    },
    "scale": {
        "basic_stats_24h": True,
        "prompt_debugger": True,
        "agent_debugger": True,
        "advanced_analytics": True,
        "compliance_gdpr": True,
        "private_deploy": False,
        "sla_security_package": False,
    },
    "enterprise": {
        "basic_stats_24h": True,
        "prompt_debugger": True,
        "agent_debugger": True,
        "advanced_analytics": True,
        "compliance_gdpr": True,
        "private_deploy": True,
        "sla_security_package": True,
    },
}

FEATURE_MIN_PLAN = {
    "basic_stats_24h": "free",
    "prompt_debugger": "starter",
    "agent_debugger": "team",
    "advanced_analytics": "team",
    "compliance_gdpr": "scale",
    "private_deploy": "enterprise",
    "sla_security_package": "enterprise",
}


@dataclass
class PlanContext:
    key: str
    raw_plan: str
    plan: str
    features: dict[str, bool]
    account_id: str | None


def normalize_plan(raw_plan: str | None) -> str:
    return PLAN_ALIAS.get((raw_plan or "free").lower(), "free")


async def resolve_plan_context(
    db: AsyncSession,
    ctx: ApiKeyContext,
) -> PlanContext:
    raw_plan = (ctx.plan or "free").lower()
    account_id: str | None = None

    account_result = await db.execute(
        select(CustomerAccount).where(CustomerAccount.api_key == ctx.key)
    )
    account = account_result.scalar_one_or_none()
    if account is not None:
        account_id = account.id
        allowed, reason = evaluate_customer_access(account)
        if not allowed:
            raise HTTPException(status_code=403, detail=f"Access blocked: {reason}")
        raw_plan = (account.plan or raw_plan or "free").lower()
    else:
        # Admin-created API keys carry their plan directly on the key. Unknown
        # public/unmanaged plans still fall back to free.
        if raw_plan not in PLAN_ALIAS:
            raw_plan = "free"

    plan = normalize_plan(raw_plan)
    features = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
    return PlanContext(
        key=ctx.key,
        raw_plan=raw_plan,
        plan=plan,
        features=features,
        account_id=account_id,
    )


async def require_plan_context(
    db: AsyncSession = Depends(get_session),
    ctx: ApiKeyContext = Depends(require_api_key_context),
) -> PlanContext:
    return await resolve_plan_context(db=db, ctx=ctx)


def require_feature(feature_key: str):
    async def _dep(
        plan_ctx: PlanContext = Depends(require_plan_context),
    ) -> PlanContext:
        if not plan_ctx.features.get(feature_key, False):
            min_plan = FEATURE_MIN_PLAN.get(feature_key, "paid")
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature_key}' requires {min_plan} plan or higher.",
            )
        return plan_ctx

    return _dep
