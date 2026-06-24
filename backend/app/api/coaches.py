"""教练 CRUD ``/api/coaches/*``（admin / staff）。"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError
from sqlalchemy import select

from ..extensions import db
from ..models import Coach, Gender
from ..schemas import CoachCreateSchema, CoachReadSchema, CoachUpdateSchema
from ..utils.auth import staff_required
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("coaches", __name__)

_read = CoachReadSchema()


@bp.get("")
@staff_required
def list_coaches():
    params = parse_page_params()
    q = request.args.get("q", "").strip()
    include_inactive = request.args.get("include_inactive") in ("1", "true", "True")

    stmt = select(Coach)
    if not include_inactive:
        stmt = stmt.where(Coach.is_active.is_(True))
    if q:
        stmt = stmt.where(Coach.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Coach.id.desc())

    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@staff_required
def create_coach():
    try:
        data = CoachCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    coach = Coach(
        name=data["name"],
        gender=Gender(data["gender"]) if data.get("gender") else None,
        phone=data.get("phone"),
        specialty=data.get("specialty"),
        bio=data.get("bio"),
        hired_at=data.get("hired_at"),
    )
    db.session.add(coach)
    db.session.commit()
    return jsonify(_read.dump(coach)), 201


@bp.get("/<int:coach_id>")
@staff_required
def retrieve_coach(coach_id: int):
    coach = db.session.get(Coach, coach_id)
    if coach is None:
        return jsonify(error="not_found"), 404
    return jsonify(_read.dump(coach))


@bp.patch("/<int:coach_id>")
@staff_required
def update_coach(coach_id: int):
    coach = db.session.get(Coach, coach_id)
    if coach is None:
        return jsonify(error="not_found"), 404

    try:
        data = CoachUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    for field in ("name", "phone", "specialty", "bio", "hired_at", "is_active"):
        if field in data:
            setattr(coach, field, data[field])
    if "gender" in data:
        coach.gender = Gender(data["gender"]) if data["gender"] else None

    db.session.commit()
    return jsonify(_read.dump(coach))


@bp.delete("/<int:coach_id>")
@staff_required
def deactivate_coach(coach_id: int):
    coach = db.session.get(Coach, coach_id)
    if coach is None:
        return jsonify(error="not_found"), 404
    coach.is_active = False
    db.session.commit()
    return jsonify(ok=True)
