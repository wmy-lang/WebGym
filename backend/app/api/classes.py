"""课程定义 ``/api/classes/*``。

- 读：member 也可看（只看 active），用于前端"可选课程"列表
- 写：staff
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError
from sqlalchemy import select

from ..extensions import db
from ..models import ClassDefinition, Coach, UserRole
from ..schemas import (
    ClassDefinitionCreateSchema,
    ClassDefinitionReadSchema,
    ClassDefinitionUpdateSchema,
)
from ..utils.auth import login_required_json, staff_required
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("classes", __name__)

_read = ClassDefinitionReadSchema()


@bp.get("")
@login_required_json
def list_classes():
    """会员只看 active；staff 可加 ``?include_inactive=1``。"""
    params = parse_page_params()
    q = request.args.get("q", "").strip()
    include_inactive = (
        current_user.role != UserRole.MEMBER
        and request.args.get("include_inactive") in ("1", "true", "True")
    )

    stmt = select(ClassDefinition)
    if not include_inactive:
        stmt = stmt.where(ClassDefinition.is_active.is_(True))
    if q:
        stmt = stmt.where(ClassDefinition.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(ClassDefinition.id.desc())

    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@staff_required
def create_class():
    try:
        data = ClassDefinitionCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if data.get("coach_id"):
        if db.session.get(Coach, data["coach_id"]) is None:
            return jsonify(error="coach_not_found"), 404

    cls = ClassDefinition(
        name=data["name"],
        description=data.get("description"),
        coach_id=data.get("coach_id"),
        capacity=data["capacity"],
        duration_minutes=data["duration_minutes"],
    )
    db.session.add(cls)
    db.session.commit()
    return jsonify(_read.dump(cls)), 201


@bp.get("/<int:class_id>")
@login_required_json
def retrieve_class(class_id: int):
    cls = db.session.get(ClassDefinition, class_id)
    if cls is None:
        return jsonify(error="not_found"), 404
    if current_user.role == UserRole.MEMBER and not cls.is_active:
        return jsonify(error="not_found"), 404
    return jsonify(_read.dump(cls))


@bp.patch("/<int:class_id>")
@staff_required
def update_class(class_id: int):
    cls = db.session.get(ClassDefinition, class_id)
    if cls is None:
        return jsonify(error="not_found"), 404

    try:
        data = ClassDefinitionUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if "coach_id" in data and data["coach_id"] is not None:
        if db.session.get(Coach, data["coach_id"]) is None:
            return jsonify(error="coach_not_found"), 404

    for field in (
        "name",
        "description",
        "coach_id",
        "capacity",
        "duration_minutes",
        "is_active",
    ):
        if field in data:
            setattr(cls, field, data[field])

    db.session.commit()
    return jsonify(_read.dump(cls))


@bp.delete("/<int:class_id>")
@staff_required
def deactivate_class(class_id: int):
    cls = db.session.get(ClassDefinition, class_id)
    if cls is None:
        return jsonify(error="not_found"), 404
    cls.is_active = False
    db.session.commit()
    return jsonify(ok=True)
