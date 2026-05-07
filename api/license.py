"""
Open-Core feature gating.

Plan hierarchy (lowest → highest):
  community → starter → team → scale

Feature matrix:
  analytics   (advanced dashboard)  → starter+
  debug       (prompt debugger)     → starter+
  traces      (agent debugger)      → starter+
  alerts      (budget alerts)       → starter+
  compliance  (GDPR/audit)          → team+

Two dependency variants:
  require_feature(feature)      → returns api_key str
  require_feature_ctx(feature)  → returns ApiKeyContext (preserves role etc.)
"""
from enum import IntEnum

from fastapi import Depends, HTTPException

from api.auth import ApiKeyContext, require_api_key_context


class Plan(IntEnum):
    COMMUNITY = 0
    STARTER = 1
    TEAM = 2
    SCALE = 3


_PLAN_LEVELS: dict[str, Plan] = {
    "community": Plan.COMMUNITY,
    "demo": Plan.STARTER,    # demo key gets starter access
    "pilot": Plan.STARTER,   # legacy → treated as starter
    "starter": Plan.STARTER,
    "team": Plan.TEAM,
    "scale": Plan.SCALE,
    "enterprise": Plan.SCALE,
}

_FEATURE_REQUIREMENTS: dict[str, Plan] = {
    "analytics": Plan.STARTER,
    "debug": Plan.STARTER,
    "traces": Plan.STARTER,
    "alerts": Plan.STARTER,
    "compliance": Plan.TEAM,
}

_UPGRADE_URL = "https://agentlens.one/#pricing"


def _resolve_plan(ctx: ApiKeyContext) -> Plan:
    return _PLAN_LEVELS.get(ctx.plan or "community", Plan.COMMUNITY)


def _check_feature(ctx: ApiKeyContext, feature: str) -> None:
    required: Plan = _FEATURE_REQUIREMENTS[feature]
    plan = _resolve_plan(ctx)
    if plan < required:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "upgrade_required",
                "message": (
                    f"This feature requires the {required.name.title()} plan or higher. "
                    f"Upgrade at {_UPGRADE_URL}"
                ),
                "required_plan": required.name.lower(),
                "current_plan": plan.name.lower(),
                "upgrade_url": _UPGRADE_URL,
            },
        )


def require_feature(feature: str):
    """Dependency that returns api_key str, raises 402 if plan insufficient."""
    async def _gate(ctx: ApiKeyContext = Depends(require_api_key_context)) -> str:
        _check_feature(ctx, feature)
        return ctx.key
    return _gate


def require_feature_ctx(feature: str):
    """Dependency that returns ApiKeyContext, raises 402 if plan insufficient."""
    async def _gate(ctx: ApiKeyContext = Depends(require_api_key_context)) -> ApiKeyContext:
        _check_feature(ctx, feature)
        return ctx
    return _gate
