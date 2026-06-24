"""会员 CRUD ``/api/members/*``（admin / staff 才能调）。

软删除：``is_active=False``，列表默认只返回 active。
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Gender, MemberProfile, User, UserRole
from ..schemas import MemberCreateSchema, MemberReadSchema, MemberUpdateSchema
from ..utils.auth import staff_required
from ..utils.crypto import encrypt
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("members", __name__)

_read = MemberReadSchema()


@bp.get("")
@staff_required
def list_members():
    """分页 + 简单关键字搜索（username / real_name / phone）。"""
    params = parse_page_params()
    q = request.args.get("q", "").strip()
    include_inactive = request.args.get("include_inactive") in ("1", "true", "True")

    stmt = select(User).where(User.role == UserRole.MEMBER)
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    if q:
        stmt = stmt.outerjoin(MemberProfile, MemberProfile.user_id == User.id).where(
            or_(
                User.username.ilike(f"%{q}%"),
                MemberProfile.real_name.ilike(f"%{q}%"),
                MemberProfile.phone.ilike(f"%{q}%"),
            )
        )
    stmt = stmt.order_by(User.id.desc())

    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@staff_required
def create_member():
    try:
        data = MemberCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if db.session.scalar(select(User).where(User.username == data["username"])):
        return jsonify(error="username_taken"), 409
    if db.session.scalar(select(MemberProfile).where(MemberProfile.phone == data["phone"])):
        return jsonify(error="phone_taken"), 409

    user = User(username=data["username"], role=UserRole.MEMBER)
    user.set_password(data["password"])

    profile = MemberProfile(
        real_name=data["real_name"],
        phone=data["phone"],
        gender=Gender(data["gender"]) if data.get("gender") else None,
        birthday=data.get("birthday"),
        emergency_contact=data.get("emergency_contact"),
        note=data.get("note"),
        id_card_encrypted=encrypt(data.get("id_card")),
    )
    user.profile = profile

    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="conflict"), 409

    return jsonify(_read.dump(user)), 201


def _get_member_or_404(member_id: int) -> User | None:
    user = db.session.get(User, member_id)
    if user is None or user.role != UserRole.MEMBER:
        return None
    return user


@bp.get("/<int:member_id>")
@staff_required
def retrieve_member(member_id: int):
    user = _get_member_or_404(member_id)
    if user is None:
        return jsonify(error="not_found"), 404
    return jsonify(_read.dump(user))


@bp.patch("/<int:member_id>")
@staff_required
def update_member(member_id: int):
    user = _get_member_or_404(member_id)
    if user is None:
        return jsonify(error="not_found"), 404

    try:
        data = MemberUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    profile = user.profile
    if profile is None:  # 防御：理论上 member 都应有 profile
        return jsonify(error="profile_missing"), 500

    if "phone" in data and data["phone"] != profile.phone:
        if db.session.scalar(
            select(MemberProfile).where(
                MemberProfile.phone == data["phone"], MemberProfile.user_id != user.id
            )
        ):
            return jsonify(error="phone_taken"), 409
        profile.phone = data["phone"]

    for field in ("real_name", "emergency_contact", "note"):
        if field in data:
            setattr(profile, field, data[field])
    if "gender" in data:
        profile.gender = Gender(data["gender"]) if data["gender"] else None
    if "birthday" in data:
        profile.birthday = data["birthday"]
    if "is_active" in data:
        user.is_active = data["is_active"]

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="conflict"), 409

    return jsonify(_read.dump(user))


@bp.delete("/<int:member_id>")
@staff_required
def deactivate_member(member_id: int):
    """软删除：将账号 is_active 置 False，保留历史卡 / 预约数据。"""
    user = _get_member_or_404(member_id)
    if user is None:
        return jsonify(error="not_found"), 404
    user.is_active = False
    db.session.commit()
    return jsonify(ok=True)
