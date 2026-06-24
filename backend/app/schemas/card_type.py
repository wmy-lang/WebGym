"""卡类型 schema。"""
from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class CardTypeCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    duration_days = fields.Int(validate=validate.Range(min=1), load_default=None)
    total_visits = fields.Int(validate=validate.Range(min=1), load_default=None)
    price = fields.Decimal(required=True, places=2, as_string=True)

    @validates_schema
    def _validate_dimension(self, data, **_):
        if data.get("duration_days") is None and data.get("total_visits") is None:
            raise ValidationError("duration_days 与 total_visits 至少填一个", field_name="duration_days")


class CardTypeUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=64))
    duration_days = fields.Int(validate=validate.Range(min=1), allow_none=True)
    total_visits = fields.Int(validate=validate.Range(min=1), allow_none=True)
    price = fields.Decimal(places=2, as_string=True)
    is_active = fields.Bool()


class CardTypeReadSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    duration_days = fields.Int(allow_none=True)
    total_visits = fields.Int(allow_none=True)
    price = fields.Decimal(places=2, as_string=True)
    is_active = fields.Bool()
