"""权限装饰器。对照 Spring Security ``@PreAuthorize("hasRole(...)")``。

未登录 → 401（让 ``login_manager.unauthorized_handler`` 处理）；
登录但角色不匹配 → 403。
"""
from __future__ import annotations

from collections.abc import Iterable
from functools import wraps

from flask import jsonify
from flask_login import current_user

from ..models import UserRole


def role_required(*roles: UserRole | str):
    """限定可访问的角色集合。

    用法::

        @bp.get("/members")
        @role_required(UserRole.ADMIN, UserRole.STAFF)
        def list_members(): ...
    """
    allowed = frozenset(_normalize(r) for r in roles)

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify(error="unauthorized"), 401
            if current_user.role not in allowed:
                return jsonify(error="forbidden"), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _normalize(role: UserRole | str) -> UserRole:
    if isinstance(role, UserRole):
        return role
    return UserRole(role)


__all__ = ["role_required"]


# 便捷别名，避免在调用处反复输入元组
def admin_required(view):
    return role_required(UserRole.ADMIN)(view)


def staff_required(view):
    """admin 也算 staff（同时拥有 staff 权限）。"""
    return role_required(UserRole.ADMIN, UserRole.STAFF)(view)


def member_required(view):
    return role_required(UserRole.MEMBER)(view)


def login_required_json(view):
    """仅校验已登录，不限角色。返回 JSON 401 而非重定向。"""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(error="unauthorized"), 401
        return view(*args, **kwargs)

    return wrapper


def has_any_role(user, roles: Iterable[UserRole | str]) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    target = frozenset(_normalize(r) for r in roles)
    return user.role in target
