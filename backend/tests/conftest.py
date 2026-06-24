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
from app.models import CardType, MemberProfile, User, UserRole
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


@pytest.fixture
def card_types(app):
    """常用卡种：年卡(期限) + 10次卡(次数)。"""
    from decimal import Decimal

    year = CardType(name="年卡", duration_days=365, price=Decimal("1888.00"))
    visit = CardType(name="10次卡", total_visits=10, price=Decimal("299.00"))
    db.session.add_all([year, visit])
    db.session.commit()
    return {"year": year.id, "visit": visit.id}


@pytest.fixture
def coach(app):
    from app.models import Coach

    c = Coach(name="李教练", specialty="瑜伽")
    db.session.add(c)
    db.session.commit()
    return c.id


@pytest.fixture
def class_def(app, coach):
    """一个标准课程定义：60 分钟、容量 5。"""
    from app.models import ClassDefinition

    cls = ClassDefinition(
        name="瑜伽入门", description="基础瑜伽", coach_id=coach, capacity=5, duration_minutes=60
    )
    db.session.add(cls)
    db.session.commit()
    return cls.id


@pytest.fixture
def future_session(app, class_def):
    """1 天后开课的 session（小容量 = 2 便于测满员）。"""
    from datetime import datetime, timedelta

    from app.models import ClassSession, SessionStatus

    start = datetime.utcnow() + timedelta(days=1)
    s = ClassSession(
        class_def_id=class_def,
        start_at=start,
        end_at=start + timedelta(hours=1),
        capacity=2,
        status=SessionStatus.SCHEDULED,
    )
    db.session.add(s)
    db.session.commit()
    return s.id


@pytest.fixture
def alice_year_card(app, seeded_users, card_types):
    """给 alice 办一张可用年卡，方便预约测试。"""
    from app.models import CardStatus, MembershipCard, User

    alice_id = db.session.query(User).filter_by(username="alice").one().id
    from datetime import date, timedelta

    card = MembershipCard(
        card_no="C20260624000001",
        member_id=alice_id,
        card_type_id=card_types["year"],
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        status=CardStatus.ACTIVE,
    )
    db.session.add(card)
    db.session.commit()
    return card.id
