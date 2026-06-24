"""Flask CLI 命令。注册到 app factory，运行：``flask --app wsgi <cmd>``。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import click
from flask import Flask
from flask.cli import with_appcontext

from .extensions import db
from .models import (
    CardStatus,
    CardType,
    ClassDefinition,
    ClassSession,
    Coach,
    Gender,
    MemberProfile,
    MembershipCard,
    SessionStatus,
    User,
    UserRole,
)


def register_cli(app: Flask) -> None:
    app.cli.add_command(seed_demo)
    app.cli.add_command(reset_db)


@click.command("seed-demo")
@click.option("--admin-password", default="admin123", show_default=True)
@click.option("--member-password", default="member123", show_default=True)
@with_appcontext
def seed_demo(admin_password: str, member_password: str) -> None:
    """写入演示数据：1 admin + 1 staff + 2 member + 2 卡种 + 2 教练 + 2 课程定义 + 1 排课。

    幂等：若用户名已存在则跳过。
    """
    created = []

    admin = _ensure_user("admin", UserRole.ADMIN, admin_password)
    created.append(("admin", admin))

    staff = _ensure_user("staff01", UserRole.STAFF, "staff123")
    created.append(("staff", staff))

    alice = _ensure_member("alice", member_password, "张爱丽", Gender.FEMALE, "13800000001")
    bob = _ensure_member("bob", member_password, "李博文", Gender.MALE, "13800000002")
    created.extend([("member", alice), ("member", bob)])

    year_card_type = _ensure_card_type("年卡", duration_days=365, price=Decimal("1999.00"))
    visit_card_type = _ensure_card_type("10 次卡", total_visits=10, price=Decimal("499.00"))

    today = date.today()
    _ensure_card("C-2026-0001", alice, year_card_type, today, today + timedelta(days=365))
    _ensure_card("V-2026-0001", bob, visit_card_type, today, end=None, visits=10)

    coach_li = _ensure_coach("李教练", Gender.FEMALE, "瑜伽,普拉提")
    coach_wang = _ensure_coach("王教练", Gender.MALE, "搏击,体能")

    yoga = _ensure_class_def("早间瑜伽", coach_li, capacity=10, duration=60)
    boxing = _ensure_class_def("拳击入门", coach_wang, capacity=8, duration=60)

    start = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1)
    _ensure_session(yoga, coach_li, start, capacity=10, location="瑜伽室 A")
    _ensure_session(boxing, coach_wang, start + timedelta(hours=2), capacity=8, location="格斗区")

    db.session.commit()

    click.echo("Seed complete.")
    click.echo(f"  admin     {admin.username} / {admin_password}")
    click.echo(f"  staff     {staff.username} / staff123")
    click.echo(f"  member    {alice.username} / {member_password}  (年卡)")
    click.echo(f"  member    {bob.username} / {member_password}  (10 次卡)")


@click.command("reset-db")
@click.confirmation_option(prompt="此操作会清空所有业务数据，确认继续？")
@with_appcontext
def reset_db() -> None:
    """DROP + CREATE 所有表。仅供开发/演示使用。"""
    db.drop_all()
    db.create_all()
    click.echo("Database reset.")


# ---- helpers -------------------------------------------------------------

def _ensure_user(username: str, role: UserRole, password: str) -> User:
    u = db.session.query(User).filter_by(username=username).first()
    if u:
        return u
    u = User(username=username, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    return u


def _ensure_member(
    username: str, password: str, real_name: str, gender: Gender, phone: str
) -> User:
    u = _ensure_user(username, UserRole.MEMBER, password)
    if u.profile is None:
        u.profile = MemberProfile(
            real_name=real_name, gender=gender, phone=phone, birthday=date(1995, 1, 1)
        )
        db.session.flush()
    return u


def _ensure_card_type(
    name: str,
    *,
    duration_days: int | None = None,
    total_visits: int | None = None,
    price: Decimal,
) -> CardType:
    ct = db.session.query(CardType).filter_by(name=name).first()
    if ct:
        return ct
    ct = CardType(
        name=name, duration_days=duration_days, total_visits=total_visits, price=price
    )
    db.session.add(ct)
    db.session.flush()
    return ct


def _ensure_card(
    card_no: str,
    member: User,
    card_type: CardType,
    start: date,
    end: date | None,
    visits: int | None = None,
) -> MembershipCard:
    c = db.session.query(MembershipCard).filter_by(card_no=card_no).first()
    if c:
        return c
    c = MembershipCard(
        card_no=card_no,
        member_id=member.id,
        card_type_id=card_type.id,
        start_date=start,
        end_date=end,
        remaining_visits=visits,
        status=CardStatus.ACTIVE,
    )
    db.session.add(c)
    db.session.flush()
    return c


def _ensure_coach(name: str, gender: Gender, specialty: str) -> Coach:
    c = db.session.query(Coach).filter_by(name=name).first()
    if c:
        return c
    c = Coach(name=name, gender=gender, specialty=specialty, hired_at=date(2024, 1, 1))
    db.session.add(c)
    db.session.flush()
    return c


def _ensure_class_def(name: str, coach: Coach, capacity: int, duration: int) -> ClassDefinition:
    cd = db.session.query(ClassDefinition).filter_by(name=name).first()
    if cd:
        return cd
    cd = ClassDefinition(
        name=name, coach_id=coach.id, capacity=capacity, duration_minutes=duration
    )
    db.session.add(cd)
    db.session.flush()
    return cd


def _ensure_session(
    cd: ClassDefinition, coach: Coach, start: datetime, capacity: int, location: str
) -> ClassSession:
    existing = (
        db.session.query(ClassSession)
        .filter_by(class_def_id=cd.id, start_at=start)
        .first()
    )
    if existing:
        return existing
    s = ClassSession(
        class_def_id=cd.id,
        coach_id=coach.id,
        start_at=start,
        end_at=start + timedelta(minutes=cd.duration_minutes),
        capacity=capacity,
        location=location,
        status=SessionStatus.SCHEDULED,
    )
    db.session.add(s)
    db.session.flush()
    return s
