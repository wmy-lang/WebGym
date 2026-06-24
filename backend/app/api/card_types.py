"""卡类型 CRUD ``/api/card-types/*``。

读：staff_required；写：admin_required（卡价是关键定价信息）。
"""
from __future__ import annotations

from decimal import Decimal

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError
from sqlalchemy import select

from ..extensions import db
from ..models import CardType
from ..schemas import CardTypeCreateSchema, CardTypeReadSchema, CardTypeUpdateSchema
from ..utils.auth import admin_required, staff_required
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("card_types", __name__)

_read = CardTypeReadSchema()


@bp.get("")
@staff_required
def list_card_types():
    params = parse_page_params()
    include_inactive = request.args.get("include_inactive") in ("1", "true", "True")

    stmt = select(CardType)
    if not include_inactive:
        stmt = stmt.where(CardType.is_active.is_(True))
    stmt = stmt.order_by(CardType.id.asc())

    return jsonify(paginate(stmt, _read.dump, params))


@bp.post("")
@admin_required
def create_card_type():
    try:
        data = CardTypeCreateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if db.session.scalar(select(CardType).where(CardType.name == data["name"])):
        return jsonify(error="name_taken"), 409

    ct = CardType(
        name=data["name"],
        duration_days=data.get("duration_days"),
        total_visits=data.get("total_visits"),
        price=Decimal(str(data["price"])),
    )
    db.session.add(ct)
    db.session.commit()
    return jsonify(_read.dump(ct)), 201


@bp.get("/<int:card_type_id>")
@staff_required
def retrieve_card_type(card_type_id: int):
    ct = db.session.get(CardType, card_type_id)
    if ct is None:
        return jsonify(error="not_found"), 404
    return jsonify(_read.dump(ct))


@bp.patch("/<int:card_type_id>")
@admin_required
def update_card_type(card_type_id: int):
    ct = db.session.get(CardType, card_type_id)
    if ct is None:
        return jsonify(error="not_found"), 404

    try:
        data = CardTypeUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    if "name" in data and data["name"] != ct.name:
        if db.session.scalar(
            select(CardType).where(CardType.name == data["name"], CardType.id != ct.id)
        ):
            return jsonify(error="name_taken"), 409
        ct.name = data["name"]

    for field in ("duration_days", "total_visits", "is_active"):
        if field in data:
            setattr(ct, field, data[field])
    if "price" in data:
        ct.price = Decimal(str(data["price"]))

    db.session.commit()
    return jsonify(_read.dump(ct))


@bp.delete("/<int:card_type_id>")
@admin_required
def deactivate_card_type(card_type_id: int):
    ct = db.session.get(CardType, card_type_id)
    if ct is None:
        return jsonify(error="not_found"), 404
    ct.is_active = False
    db.session.commit()
    return jsonify(ok=True)
