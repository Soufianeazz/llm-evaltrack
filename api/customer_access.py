import time

from storage.models import CustomerAccount

BLOCKED_SUBSCRIPTION_STATUSES = {
    "past_due",
    "canceled",
    "unpaid",
    "incomplete",
    "incomplete_expired",
    "paused",
}
ALLOWED_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def evaluate_customer_access(account: CustomerAccount, now: float | None = None) -> tuple[bool, str]:
    ts = now if now is not None else time.time()

    if (account.status or "pending") != "approved":
        return False, account.status or "pending"

    access_state = (account.access_state or "").lower()
    if access_state in {"suspended", "past_due", "canceled", "rejected"}:
        return False, access_state

    sub_status = (account.subscription_status or "").lower()
    if sub_status in BLOCKED_SUBSCRIPTION_STATUSES:
        return False, sub_status
    if sub_status in ALLOWED_SUBSCRIPTION_STATUSES:
        return True, sub_status

    if account.trial_ends_at is not None:
        if ts <= account.trial_ends_at:
            return True, "trialing"
        return False, "trial_expired"

    return False, "inactive"
