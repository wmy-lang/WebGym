"""配置类：Dev / Test / Prod 三套，靠 ``FLASK_CONFIG`` 环境变量切换。"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BACKEND_DIR / "instance"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 会话 cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # 生产覆盖为 True

    # CSRF
    WTF_CSRF_TIME_LIMIT = None  # session 期内有效

    # CORS：仅允许前端 dev server
    CORS_ORIGINS = ["http://localhost:5173"]
    CORS_SUPPORTS_CREDENTIALS = True


class DevConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{INSTANCE_DIR / 'webgym.db'}"


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProdConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'webgym.db'}"
    )


CONFIGS: dict[str, type[BaseConfig]] = {
    "dev": DevConfig,
    "test": TestConfig,
    "prod": ProdConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    name = name or os.environ.get("FLASK_CONFIG", "dev")
    return CONFIGS.get(name, DevConfig)
