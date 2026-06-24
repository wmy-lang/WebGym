"""敏感字段加密（身份证号等）。对应 Spring 的 ``@Convert`` + AES。

Fernet 是 cryptography 包提供的对称加密：32-byte urlsafe-base64 key、
内含 HMAC 防篡改、带时间戳。生产环境密钥应放进 KMS / 环境变量。
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _get_fernet() -> Fernet:
    key = current_app.config.get("FIELD_ENC_KEY")
    if not key:
        # Dev/Test：从 SECRET_KEY 派生一个稳定的 32 字节 key
        secret = current_app.config["SECRET_KEY"]
        derived = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(derived)
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt(plain: str | None) -> str | None:
    if plain is None or plain == "":
        return None
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None
