"""会员卡 schema。"""
from __future__ import annotations

from marshmallow import Schema, fields, validate


class CardIssueSchema(Schema):
    """办卡入参。"""

    member_id = fields.Int(required=True, validate=validate.Range(min=1))
    card_type_id = fields.Int(required=True, validate=validate.Range(min=1))
    start_date = fields.Date(load_default=None)


class CardReadSchema(Schema):
    id = fields.Int()
    card_no = fields.Str()
    member_id = fields.Int()
    member_name = fields.Method("get_member_name")
    card_type_id = fields.Int()
    card_type_name = fields.Method("get_card_type_name")
    start_date = fields.Date()
    end_date = fields.Date(allow_none=True)
    remaining_visits = fields.Int(allow_none=True)
    status = fields.Method("get_status")
    issued_by = fields.Int(allow_none=True)
    issued_at = fields.DateTime()
    frozen_at = fields.DateTime(allow_none=True)

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_member_name(self, obj):
        profile = getattr(obj.member, "profile", None) if obj.member else None
        return profile.real_name if profile else None

    def get_card_type_name(self, obj):
        return obj.card_type.name if obj.card_type else None
