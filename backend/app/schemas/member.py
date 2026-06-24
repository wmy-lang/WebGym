"""会员 schema。会员账号 = User(role=member) + MemberProfile 1:1。"""
from __future__ import annotations

from marshmallow import Schema, fields, validate


class MemberCreateSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))
    real_name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    phone = fields.Str(required=True, validate=validate.Length(min=5, max=32))
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other"]), load_default=None)
    birthday = fields.Date(load_default=None)
    id_card = fields.Str(validate=validate.Length(max=32), load_default=None)
    emergency_contact = fields.Str(validate=validate.Length(max=64), load_default=None)
    note = fields.Str(load_default=None)


class MemberUpdateSchema(Schema):
    real_name = fields.Str(validate=validate.Length(min=1, max=64))
    phone = fields.Str(validate=validate.Length(min=5, max=32))
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other"]), allow_none=True)
    birthday = fields.Date(allow_none=True)
    emergency_contact = fields.Str(validate=validate.Length(max=64), allow_none=True)
    note = fields.Str(allow_none=True)
    is_active = fields.Bool()


class MemberReadSchema(Schema):
    """会员出参。把 User + MemberProfile 拍平成一层。"""

    id = fields.Int()
    username = fields.Str()
    role = fields.Method("get_role")
    is_active = fields.Bool()
    real_name = fields.Method("get_real_name")
    phone = fields.Method("get_phone")
    gender = fields.Method("get_gender")
    birthday = fields.Method("get_birthday")
    emergency_contact = fields.Method("get_emergency_contact")
    note = fields.Method("get_note")
    created_at = fields.DateTime()
    last_login_at = fields.DateTime(allow_none=True)

    def get_role(self, obj):
        return obj.role.value if obj.role else None

    def _profile(self, obj):
        return getattr(obj, "profile", None)

    def get_real_name(self, obj):
        p = self._profile(obj)
        return p.real_name if p else None

    def get_phone(self, obj):
        p = self._profile(obj)
        return p.phone if p else None

    def get_gender(self, obj):
        p = self._profile(obj)
        return p.gender.value if p and p.gender else None

    def get_birthday(self, obj):
        p = self._profile(obj)
        return p.birthday.isoformat() if p and p.birthday else None

    def get_emergency_contact(self, obj):
        p = self._profile(obj)
        return p.emergency_contact if p else None

    def get_note(self, obj):
        p = self._profile(obj)
        return p.note if p else None
