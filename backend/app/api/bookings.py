"""预约 ``/api/bookings/*``。

- 会员：list 只看自己 / 自助 create / 自助 cancel（受 2h 截止限制）
- staff/admin：list 任意 / 代下单 / 强制取消
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    Booking,
    BookingSource,
    BookingStatus,
    ClassSession,
    MembershipCard,
    User,
    UserRole,
)
from ..schemas import BookingCreateSchema, BookingReadSchema
from ..services import booking_service
from ..services.booking_service import BookingError, BookingInput
from ..utils.auth import login_required_json
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("bookings", __name__)

_read = BookingReadSchema()


def _base_stmt():
    return select(Booking).options(
        selectinload(Booking.member).selectinload(User.profile),
        selectinload(Booking.session).selectinload(ClassSession.class_def),
        selectinload(Booking.card).selectinload(MembershipCard.card_type),
        selectinload(Booking.attendance),
    )


@bp.get("")
@login_required_json
def list_bookings():
    params = parse_page_params()
    stmt = _base_stmt()

    if current_user.role == UserRole.MEMBER:
        stmt = stmt.where(Booking.member_id == current_user.id)
    else:
        member_id = request.args.get("member_id", type=int)
        if member_id is not None:
            stmt = stmt.where(Booking.member_id == member_id)
        session_id = request.args.get("session_id", type=int)
        if session_id is not None:
            stmt = stmt.where(Booking.session_id == session_id)

    status = request.args.get("status")
    if status:
        try:
            stmt = stmt.where(Booking.status == BookingStatus(status))
        except ValueError:
            return jsonify(error="invalid_status"), 400

    stmt = stmt.order_by(Booking.id.desc())
    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@login_required_json
def create_booking():
    try:
        data = BookingCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    # 会员只能给自己预约；staff/admin 可指定 member_id 代下单
    if current_user.role == UserRole.MEMBER:
        if data.get("member_id") is not None and data["member_id"] != current_user.id:
            return jsonify(error="forbidden"), 403
        member_id = current_user.id
        source = BookingSource.SELF
    else:
        if data.get("member_id") is None:
            return jsonify(error="validation_error", details={"member_id": ["必填"]}), 400
        member_id = data["member_id"]
        source = BookingSource.ADMIN

    try:
        b = booking_service.book_session(
            BookingInput(member_id=member_id, session_id=data["session_id"], source=source)
        )
    except BookingError as e:
        return jsonify(error=e.code), e.status_code

    db.session.refresh(b)
    return jsonify(_read.dump(b)), 201


@bp.get("/<int:booking_id>")
@login_required_json
def retrieve_booking(booking_id: int):
    b = db.session.get(Booking, booking_id)
    if b is None:
        return jsonify(error="not_found"), 404
    if current_user.role == UserRole.MEMBER and b.member_id != current_user.id:
        return jsonify(error="forbidden"), 403
    return jsonify(_read.dump(b))


@bp.post("/<int:booking_id>/cancel")
@login_required_json
def cancel_booking(booking_id: int):
    try:
        b = booking_service.cancel_booking(
            booking_id, actor_id=current_user.id, actor_role=current_user.role
        )
    except BookingError as e:
        return jsonify(error=e.code), e.status_code
    return jsonify(_read.dump(b))
