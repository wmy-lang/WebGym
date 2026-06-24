"""课程 + 排课 schema。"""
from __future__ import annotations

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


# ---------- ClassDefinition ----------


class ClassDefinitionCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    description = fields.Str(load_default=None)
    coach_id = fields.Int(validate=validate.Range(min=1), load_default=None)
    capacity = fields.Int(validate=validate.Range(min=1, max=500), load_default=10)
    duration_minutes = fields.Int(validate=validate.Range(min=10, max=480), load_default=60)


class ClassDefinitionUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=64))
    description = fields.Str(allow_none=True)
    coach_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    capacity = fields.Int(validate=validate.Range(min=1, max=500))
    duration_minutes = fields.Int(validate=validate.Range(min=10, max=480))
    is_active = fields.Bool()


class ClassDefinitionReadSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    coach_id = fields.Int(allow_none=True)
    coach_name = fields.Method("get_coach_name")
    capacity = fields.Int()
    duration_minutes = fields.Int()
    is_active = fields.Bool()

    def get_coach_name(self, obj):
        return obj.coach.name if obj.coach else None


# ---------- ClassSession ----------


class ClassSessionCreateSchema(Schema):
    class_def_id = fields.Int(required=True, validate=validate.Range(min=1))
    start_at = fields.DateTime(required=True)
    end_at = fields.DateTime(load_default=None)
    coach_id = fields.Int(validate=validate.Range(min=1), load_default=None)
    capacity = fields.Int(validate=validate.Range(min=1, max=500), load_default=None)
    location = fields.Str(validate=validate.Length(max=64), load_default=None)

    @validates_schema
    def _validate_times(self, data, **_):
        end = data.get("end_at")
        if end is not None and end <= data["start_at"]:
            raise ValidationError("end_at 必须晚于 start_at", field_name="end_at")


class ClassSessionUpdateSchema(Schema):
    start_at = fields.DateTime()
    end_at = fields.DateTime()
    coach_id = fields.Int(validate=validate.Range(min=1), allow_none=True)
    capacity = fields.Int(validate=validate.Range(min=1, max=500))
    location = fields.Str(validate=validate.Length(max=64), allow_none=True)


class ClassSessionReadSchema(Schema):
    id = fields.Int()
    class_def_id = fields.Int()
    class_name = fields.Method("get_class_name")
    coach_id = fields.Int(allow_none=True)
    coach_name = fields.Method("get_coach_name")
    start_at = fields.DateTime()
    end_at = fields.DateTime()
    capacity = fields.Int()
    location = fields.Str(allow_none=True)
    status = fields.Method("get_status")
    booked_count = fields.Method("get_booked_count")

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_class_name(self, obj):
        return obj.class_def.name if obj.class_def else None

    def get_coach_name(self, obj):
        return obj.coach.name if obj.coach else None

    def get_booked_count(self, obj):
        # 已计算到属性上则用之；否则数关系
        cached = getattr(obj, "_booked_count", None)
        if cached is not None:
            return cached
        from app.models import BookingStatus

        return sum(1 for b in obj.bookings if b.status != BookingStatus.CANCELLED)
