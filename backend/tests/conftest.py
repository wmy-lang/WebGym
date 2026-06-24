"""pytest 全局 fixture。

- ``app`` / ``client``: 干净的应用 + 内存库 schema（不 seed 任何数据）
- ``seeded_users``: 额外注入 admin / staff01 / alice 三个账号
- ``login`` 辅助函数：登录后保留 cookie
"""
from __future__ import annotations

import pytest
from flask import Blueprint, jsonify

from app import create_app
from app.extensions import db
from app.models import MemberProfile, User, UserRole
from app.utils.auth import admin_required, member_required, role_required, staff_required


@pytest.fixture
def app():
    app = create_app("test")

    # 临时挂用于装饰器测试的探针蓝图
    probe = Blueprint("_probe", __name__)

    @probe.get("/admin-only")
    @admin_required
    def _admin():
        return jsonify(ok=True)

    @probe.get("/staff-only")
    @staff_required
    def _staff():
        return jsonify(ok=True)

    @probe.get("/member-only")
    @member_required
    def _member():
        return jsonify(ok=True)

    @probe.get("/any-role")
    @role_required(UserRole.ADMIN, UserRole.MEMBER)
    def _any():
        return jsonify(ok=True)

    app.register_blueprint(probe, url_prefix="/_probe")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_users(app):
    """认证类测试用：写入 admin / staff01 / alice。"""
    for username, role, password in [
        ("admin", UserRole.ADMIN, "admin123"),
        ("staff01", UserRole.STAFF, "staff123"),
        ("alice", UserRole.MEMBER, "member123"),
    ]:
        u = User(username=username, role=role)
        u.set_password(password)
        if role == UserRole.MEMBER:
            u.profile = MemberProfile(real_name="张爱丽", phone="13900000001")
        db.session.add(u)
    db.session.commit()


def login(client, username: str, password: str):
    """登录并返回原始 response，cookie 自动保留在 client 上。"""
    return client.post("/api/auth/login", json={"username": username, "password": password})


@pytest.fixture
def do_login(client):
    """fixture 形态：``do_login('alice', 'member123')``。"""

    def _do(username: str, password: str):
        return login(client, username, password)

    return _do
