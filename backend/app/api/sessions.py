"""排课 ``/api/sessions/*``。

- 读：已登录用户可看（前端列出可预约的 session）
- 写：staff
- 不允许直接 DELETE：用 ``POST /:id/cancel`` 切状态
"""
from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    Booking,
    BookingStatus,
    ClassDefinition,
    ClassSession,
    Coach,
    SessionStatus,
)
from ..schemas import (
    ClassSessionCreateSchema,
    ClassSessionReadSchema,
    ClassSessionUpdateSchema,
)
from ..utils.auth import login_required_json, staff_required
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("sessions", __name__)

_read = ClassSessionReadSchema()


def _attach_booked_counts(rows):
    """批量统计每个 session 当前有效预约人数，挂到对象上以便 schema 序列化。"""
    if not rows:
        return rows
    ids = [r.id for r in rows]
    counts = dict(
        db.session.execute(
            select(Booking.session_id, func.count(Booking.id))
            .where(Booking.session_id.in_(ids))
            .where(Booking.status != BookingStatus.CANCELLED)
            .group_by(Booking.session_id)
        ).all()
    )
    for r in rows:
        r._booked_count = counts.get(r.id, 0)
    return rows


def _parse_dt(name: str):
    value = request.args.get(name)
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return ...  # sentinel：调用方判断


def _serialize_one(s: ClassSession) -> dict:
    _attach_booked_counts([s])
    return _read.dump(s)


@bp.get("")
@login_required_json
def list_sessions():
    """常用过滤：``?from=2026-07-01&to=2026-07-31&class_def_id=&coach_id=&status=``。"""
    params = parse_page_params()
    stmt = select(ClassSession).options(
        selectinload(ClassSession.class_def),
        selectinload(ClassSession.coach),
    )

    from_dt = _parse_dt("from")
    to_dt = _parse_dt("to")
    if from_dt is ... or to_dt is ...:
        return jsonify(error="invalid_datetime"), 400
    if from_dt is not None:
        stmt = stmt.where(ClassSession.start_at >= from_dt)
    if to_dt is not None:
        stmt = stmt.where(ClassSession.start_at < to_dt)

    class_def_id = request.args.get("class_def_id", type=int)
    if class_def_id is not None:
        stmt = stmt.where(ClassSession.class_def_id == class_def_id)
    coach_id = request.args.get("coach_id", type=int)
    if coach_id is not None:
        stmt = stmt.where(ClassSession.coach_id == coach_id)
    status = request.args.get("status")
    if status:
        try:
            stmt = stmt.where(ClassSession.status == SessionStatus(status))
        except ValueError:
            return jsonify(error="invalid_status"), 400

    stmt = stmt.order_by(ClassSession.start_at.asc())

    # 先拿原始行，再统一挂 booked_count，再 dump
    result = paginate(stmt, lambda x: x, params)
    rows = result["items"]
    _attach_booked_counts(rows)
    result["items"] = [_read.dump(r) for r in rows]
    return jsonify(result)


@bp.post("")
@staff_required
def create_session():
    try:
        data = ClassSessionCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    cls = db.session.get(ClassDefinition, data["class_def_id"])
    if cls is None or not cls.is_active:
        return jsonify(error="class_not_found"), 404

    coach_id = data.get("coach_id") if data.get("coach_id") is not None else cls.coach_id
    if coach_id is not None and db.session.get(Coach, coach_id) is None:
        return jsonify(error="coach_not_found"), 404

    capacity = data.get("capacity") or cls.capacity
    start_at = data["start_at"]
    end_at = data.get("end_at") or (start_at + timedelta(minutes=cls.duration_minutes))

    sess = ClassSession(
        class_def_id=cls.id,
        coach_id=coach_id,
        start_at=start_at,
        end_at=end_at,
        capacity=capacity,
        location=data.get("location"),
        status=SessionStatus.SCHEDULED,
    )
    db.session.add(sess)
    db.session.commit()
    return jsonify(_serialize_one(sess)), 201


@bp.get("/<int:session_id>")
@login_required_json
def retrieve_session(session_id: int):
    s = db.session.get(ClassSession, session_id)
    if s is None:
        return jsonify(error="not_found"), 404
    return jsonify(_serialize_one(s))


@bp.patch("/<int:session_id>")
@staff_required
def update_session(session_id: int):
    s = db.session.get(ClassSession, session_id)
    if s is None:
        return jsonify(error="not_found"), 404
    if s.status != SessionStatus.SCHEDULED:
        return jsonify(error="session_not_scheduled"), 400

    try:
        data = ClassSessionUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if "coach_id" in data and data["coach_id"] is not None:
        if db.session.get(Coach, data["coach_id"]) is None:
            return jsonify(error="coach_not_found"), 404

    new_start = data.get("start_at", s.start_at)
    new_end = data.get("end_at", s.end_at)
    if new_end <= new_start:
        return (
            jsonify(error="validation_error", details={"end_at": ["end_at 必须晚于 start_at"]}),
            400,
        )

    for field in ("start_at", "end_at", "coach_id", "capacity", "location"):
        if field in data:
            setattr(s, field, data[field])

    db.session.commit()
    return jsonify(_serialize_one(s))


@bp.post("/<int:session_id>/cancel")
@staff_required
def cancel_session(session_id: int):
    s = db.session.get(ClassSession, session_id)
    if s is None:
        return jsonify(error="not_found"), 404
    if s.status != SessionStatus.SCHEDULED:
        return jsonify(error="session_not_scheduled"), 400

    s.status = SessionStatus.CANCELLED
    # 连带把这堂课所有"已预约"状态的 booking 也置 cancelled
    for b in s.bookings:
        if b.status == BookingStatus.BOOKED:
            b.status = BookingStatus.CANCELLED
            b.cancelled_at = datetime.utcnow()
    db.session.commit()
    return jsonify(_serialize_one(s))


@bp.post("/<int:session_id>/finish")
@staff_required
def finish_session(session_id: int):
    s = db.session.get(ClassSession, session_id)
    if s is None:
        return jsonify(error="not_found"), 404
    if s.status != SessionStatus.SCHEDULED:
        return jsonify(error="session_not_scheduled"), 400

    s.status = SessionStatus.FINISHED
    # 未签到的预约置 no_show（签到流程在 W7）
    for b in s.bookings:
        if b.status == BookingStatus.BOOKED:
            b.status = BookingStatus.NO_SHOW
    db.session.commit()
    return jsonify(_serialize_one(s))
