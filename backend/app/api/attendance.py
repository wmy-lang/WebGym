"""签到 ``/api/attendance/*``。

- POST /api/attendance ``{booking_id}``：签到。会员只能为自己签。
- GET  /api/attendance：查签到记录。member 只看自己；staff 可按 session / member 过滤。
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Attendance, Booking, ClassSession, User, UserRole
from ..schemas import AttendanceReadSchema
from ..services import booking_service
from ..services.booking_service import BookingError
from ..utils.auth import login_required_json
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("attendance", __name__)

_read = AttendanceReadSchema()


def _base_stmt():
    return select(Attendance).options(
        selectinload(Attendance.booking)
        .selectinload(Booking.member)
        .selectinload(User.profile),
        selectinload(Attendance.booking)
        .selectinload(Booking.session)
        .selectinload(ClassSession.class_def),
    )


@bp.get("")
@login_required_json
def list_attendance():
    params = parse_page_params()
    stmt = _base_stmt().join(Attendance.booking)

    if current_user.role == UserRole.MEMBER:
        stmt = stmt.where(Booking.member_id == current_user.id)
    else:
        member_id = request.args.get("member_id", type=int)
        if member_id is not None:
            stmt = stmt.where(Booking.member_id == member_id)
        session_id = request.args.get("session_id", type=int)
        if session_id is not None:
            stmt = stmt.where(Booking.session_id == session_id)

    stmt = stmt.order_by(Attendance.id.desc())
    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@login_required_json
def check_in():
    payload = request.get_json(silent=True) or {}
    booking_id = payload.get("booking_id")
    if not isinstance(booking_id, int) or booking_id <= 0:
        return jsonify(error="validation_error", details={"booking_id": ["必填"]}), 400

    try:
        att = booking_service.check_in(
            booking_id, operator_id=current_user.id, operator_role=current_user.role
        )
    except BookingError as e:
        return jsonify(error=e.code), e.status_code

    db.session.refresh(att)
    return jsonify(_read.dump(att)), 201
