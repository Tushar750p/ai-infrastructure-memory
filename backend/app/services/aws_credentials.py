import boto3
from cryptography.fernet import Fernet


def encrypt_secret(value: str, encryption_key: str) -> str:
    return Fernet(encryption_key.encode()).encrypt(value.encode()).decode()


def decrypt_secret(value: str, encryption_key: str) -> str:
    return Fernet(encryption_key.encode()).decrypt(value.encode()).decode()


def build_aws_session(access_key_id: str, secret_access_key: str, region: str):
    return boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )


def build_role_session(
    role_arn: str,
    external_id: str | None,
    region: str,
    duration_seconds: int = 900,
):
    sts = boto3.client("sts", region_name=region)
    assume_kwargs = {
        "RoleArn": role_arn,
        "RoleSessionName": "aime-infrastructure-memory",
        "DurationSeconds": duration_seconds,
    }
    if external_id:
        assume_kwargs["ExternalId"] = external_id

    credentials = sts.assume_role(**assume_kwargs)["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region,
    )


def build_account_session(account, encryption_key: str, duration_seconds: int = 900):
    if account.credential_mode == "role":
        if not account.role_arn:
            raise ValueError("AWS role credential mode requires role_arn")
        return build_role_session(
            account.role_arn,
            decrypt_secret(account.external_id, encryption_key) if account.external_id else None,
            account.region,
            duration_seconds,
        )

    if not account.encrypted_access_key_id or not account.encrypted_secret_access_key:
        raise ValueError("AWS access-key credential mode requires encrypted credentials")

    return build_aws_session(
        decrypt_secret(account.encrypted_access_key_id, encryption_key),
        decrypt_secret(account.encrypted_secret_access_key, encryption_key),
        account.region,
    )
