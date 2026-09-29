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
