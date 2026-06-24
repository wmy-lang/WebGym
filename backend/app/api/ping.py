"""健康检查蓝图：``GET /api/ping``。

骨架期用来确认 app factory、蓝图注册、JSON 响应链路通畅。
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify

bp = Blueprint("ping", __name__)


@bp.get("/ping")
def ping():
    return jsonify(
        status="ok",
        service="webgym-backend",
        config=current_app.config.get("ENV_NAME", "dev"),
        time=datetime.now(timezone.utc).isoformat(),
    )
