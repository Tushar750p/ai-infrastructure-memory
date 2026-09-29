from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError

from app.models.aws_account import AWSAccount
from app.services.aws_credentials import build_account_session


def check_account_health(
    account: AWSAccount,
    encryption_key: str,
    duration_seconds: int = 900,
) -> tuple[str, str | None]:
    try:
        session = build_account_session(
            account,
            encryption_key,
            duration_seconds=duration_seconds,
        )
        identity = session.client("sts", region_name=account.region).get_caller_identity()
        if identity.get("Account") != account.account_id:
            return "unhealthy", "AWS account identity does not match the connected account"
        return "healthy", None
    except (BotoCoreError, ClientError, ValueError) as exc:
        return "unhealthy", str(exc)[:1000]


def update_account_health(
    account: AWSAccount,
    encryption_key: str,
    duration_seconds: int = 900,
) -> str:
    status, error = check_account_health(account, encryption_key, duration_seconds)
    account.last_health_check_at = datetime.now(timezone.utc)
    account.last_health_status = status
    account.last_health_error = error
    return status
