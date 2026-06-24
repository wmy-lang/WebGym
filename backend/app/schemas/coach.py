"""教练 schema。"""
from __future__ import annotations

from marshmallow import Schema, fields, validate


class CoachCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other"]), load_default=None)
    phone = fields.Str(validate=validate.Length(max=32), load_default=None)
    specialty = fields.Str(validate=validate.Length(max=255), load_default=None)
    bio = fields.Str(load_default=None)
    hired_at = fields.Date(load_default=None)


class CoachUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=64))
    gender = fields.Str(validate=validate.OneOf(["male", "female", "other"]), allow_none=True)
    phone = fields.Str(validate=validate.Length(max=32), allow_none=True)
    specialty = fields.Str(validate=validate.Length(max=255), allow_none=True)
    bio = fields.Str(allow_none=True)
    hired_at = fields.Date(allow_none=True)
    is_active = fields.Bool()


class CoachReadSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    gender = fields.Method("get_gender")
    phone = fields.Str(allow_none=True)
    specialty = fields.Str(allow_none=True)
    bio = fields.Str(allow_none=True)
    hired_at = fields.Date(allow_none=True)
    is_active = fields.Bool()
    created_at = fields.DateTime()

    def get_gender(self, obj):
        return obj.gender.value if obj.gender else None
