"""会员卡 API ``/api/cards/*``。

权限：
- staff/admin：办卡、续费、冻结/解冻、注销、查所有
- member：只能看自己名下的卡
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import CardStatus, MembershipCard, User, UserRole
from ..schemas import CardIssueSchema, CardReadSchema
from ..services import card_service
from ..services.card_service import CardError, IssueInput
from ..utils.auth import login_required_json, staff_required
from ..utils.pagination import paginate, parse_page_params

bp = Blueprint("cards", __name__)

_read = CardReadSchema()


def _base_stmt():
    return select(MembershipCard).options(
        selectinload(MembershipCard.member).selectinload(User.profile),
        selectinload(MembershipCard.card_type),
    )


@bp.get("")
@login_required_json
def list_cards():
    """staff 可看全部 + 按 member_id 过滤；member 只能看自己。"""
    params = parse_page_params()
    stmt = _base_stmt()

    if current_user.role == UserRole.MEMBER:
        stmt = stmt.where(MembershipCard.member_id == current_user.id)
    else:
        member_id = request.args.get("member_id", type=int)
        if member_id is not None:
            stmt = stmt.where(MembershipCard.member_id == member_id)
        status = request.args.get("status")
        if status:
            try:
                stmt = stmt.where(MembershipCard.status == CardStatus(status))
            except ValueError:
                return jsonify(error="invalid_status"), 400

    stmt = stmt.order_by(MembershipCard.id.desc())
    return jsonify(paginate(stmt, _read.dump, params))


@bp.get("/<int:card_id>")
@login_required_json
def retrieve_card(card_id: int):
    card = db.session.get(MembershipCard, card_id)
    if card is None:
        return jsonify(error="not_found"), 404
    if current_user.role == UserRole.MEMBER and card.member_id != current_user.id:
        return jsonify(error="forbidden"), 403
    return jsonify(_read.dump(card))


@bp.post("")
@staff_required
def issue_card():
    try:
        data = CardIssueSchema().load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify(error="validation_error", details=e.messages), 400

    try:
        card = card_service.issue_card(
            IssueInput(
                member_id=data["member_id"],
                card_type_id=data["card_type_id"],
                start_date=data.get("start_date"),
                issued_by_id=current_user.id,
            )
        )
    except CardError as e:
        return jsonify(error=e.code), e.status_code

    return jsonify(_read.dump(card)), 201


def _action(handler, card_id: int):
    try:
        card = handler(card_id)
    except CardError as e:
        return jsonify(error=e.code), e.status_code
    return jsonify(_read.dump(card))


@bp.post("/<int:card_id>/renew")
@staff_required
def renew_card(card_id: int):
    return _action(card_service.renew_card, card_id)


@bp.post("/<int:card_id>/freeze")
@staff_required
def freeze_card(card_id: int):
    return _action(card_service.freeze_card, card_id)


@bp.post("/<int:card_id>/unfreeze")
@staff_required
def unfreeze_card(card_id: int):
    return _action(card_service.unfreeze_card, card_id)


@bp.post("/<int:card_id>/cancel")
@staff_required
def cancel_card(card_id: int):
    return _action(card_service.cancel_card, card_id)


@bp.post("/sweep-expired")
@staff_required
def sweep_expired():
    """把已到期卡批量置 expired。手动 / 定时任务可调。"""
    affected = card_service.sweep_expired()
    return jsonify(affected=affected)
