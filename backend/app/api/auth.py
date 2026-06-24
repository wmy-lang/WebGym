"""认证蓝图 ``/api/auth/*``。

对照 Spring Security：
- POST /login  ≈ ``UsernamePasswordAuthenticationFilter``
- POST /logout ≈ ``LogoutFilter``
- GET  /me     ≈ ``SecurityContextHolder.getContext().getAuthentication()``
- GET  /csrf-token ≈ ``CsrfTokenRepository`` 下发 token
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from ..extensions import csrf, db
from ..models import User

bp = Blueprint("auth", __name__)


def _serialize(u: User) -> dict:
    profile = u.profile
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role.value,
        "is_active": u.is_active,
        "real_name": profile.real_name if profile else None,
        "phone": profile.phone if profile else None,
    }


@bp.get("/csrf-token")
def csrf_token():
    """获取 CSRF token。SPA 启动时先调一次，axios 拦截器塞进 X-CSRFToken。"""
    return jsonify(csrf_token=generate_csrf())


@bp.post("/login")
@csrf.exempt  # 登录前还没拿到 cookie；用速率限制 + Cookie SameSite 防 CSRF（W11 加 Limiter）
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify(error="invalid_credentials"), 400

    user = db.session.query(User).filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify(error="invalid_credentials"), 401
    if not user.is_active:
        return jsonify(error="account_disabled"), 403

    login_user(user)
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    resp = jsonify(user=_serialize(user))
    # 登录成功时一并下发新 CSRF token，前端可以立即用
    resp.headers["X-CSRFToken"] = generate_csrf()
    return resp


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)


@bp.get("/me")
@login_required
def me():
    return jsonify(user=_serialize(current_user))
