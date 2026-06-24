"""预约 + 签到 schema。"""
from __future__ import annotations

from marshmallow import Schema, fields, validate


class BookingCreateSchema(Schema):
    """会员自助预约只需 session_id；staff/admin 代订时可传 member_id。"""

    session_id = fields.Int(required=True, validate=validate.Range(min=1))
    member_id = fields.Int(validate=validate.Range(min=1), load_default=None)


class BookingReadSchema(Schema):
    id = fields.Int()
    member_id = fields.Int()
    member_name = fields.Method("get_member_name")
    session_id = fields.Int()
    class_name = fields.Method("get_class_name")
    start_at = fields.Method("get_start_at")
    end_at = fields.Method("get_end_at")
    card_id = fields.Int(allow_none=True)
    card_no = fields.Method("get_card_no")
    status = fields.Method("get_status")
    source = fields.Method("get_source")
    booked_at = fields.DateTime()
    cancelled_at = fields.DateTime(allow_none=True)
    checked_in_at = fields.Method("get_checked_in_at")

    def get_status(self, obj):
        return obj.status.value if obj.status else None

    def get_source(self, obj):
        return obj.source.value if obj.source else None

    def get_member_name(self, obj):
        profile = getattr(obj.member, "profile", None) if obj.member else None
        return profile.real_name if profile else None

    def get_class_name(self, obj):
        return obj.session.class_def.name if obj.session and obj.session.class_def else None

    def get_start_at(self, obj):
        return obj.session.start_at.isoformat() if obj.session else None

    def get_end_at(self, obj):
        return obj.session.end_at.isoformat() if obj.session else None

    def get_card_no(self, obj):
        return obj.card.card_no if obj.card else None

    def get_checked_in_at(self, obj):
        return obj.attendance.checked_in_at.isoformat() if obj.attendance else None


class AttendanceReadSchema(Schema):
    id = fields.Int()
    booking_id = fields.Int()
    member_id = fields.Method("get_member_id")
    member_name = fields.Method("get_member_name")
    session_id = fields.Method("get_session_id")
    class_name = fields.Method("get_class_name")
    checked_in_at = fields.DateTime()
    checked_in_by = fields.Int(allow_none=True)

    def get_member_id(self, obj):
        return obj.booking.member_id if obj.booking else None

    def get_member_name(self, obj):
        if not obj.booking or not obj.booking.member:
            return None
        profile = getattr(obj.booking.member, "profile", None)
        return profile.real_name if profile else None

    def get_session_id(self, obj):
        return obj.booking.session_id if obj.booking else None

    def get_class_name(self, obj):
        if not obj.booking or not obj.booking.session or not obj.booking.session.class_def:
            return None
        return obj.booking.session.class_def.name
