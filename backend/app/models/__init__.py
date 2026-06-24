"""模型聚合导出。

通过在此文件统一 import，可以保证 ``flask db migrate`` 能扫到全部模型。
"""
from .attendance import Attendance
from .booking import Booking, BookingSource, BookingStatus
from .card import CardStatus, CardType, MembershipCard
from .class_ import ClassDefinition, ClassSession, SessionStatus
from .coach import Coach
from .member import Gender, MemberProfile
from .user import User, UserRole

__all__ = [
    "Attendance",
    "Booking",
    "BookingSource",
    "BookingStatus",
    "CardStatus",
    "CardType",
    "ClassDefinition",
    "ClassSession",
    "Coach",
    "Gender",
    "MemberProfile",
    "MembershipCard",
    "SessionStatus",
    "User",
    "UserRole",
]
