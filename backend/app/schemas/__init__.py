"""Marshmallow schemas —— 对照 Spring Boot 的 DTO + Bean Validation。

每个资源给三套：
- ``XxxCreateSchema``: 创建时输入，必填字段做 ``required=True``
- ``XxxUpdateSchema``: 更新时输入，``partial=True`` 允许局部字段
- ``XxxReadSchema``: 出参，包含派生字段（real_name 等）

校验失败 → ``marshmallow.ValidationError``，路由层捕获返回 400。
"""
from .card import CardIssueSchema, CardReadSchema
from .card_type import CardTypeCreateSchema, CardTypeReadSchema, CardTypeUpdateSchema
from .coach import CoachCreateSchema, CoachReadSchema, CoachUpdateSchema
from .member import MemberCreateSchema, MemberReadSchema, MemberUpdateSchema

__all__ = [
    "CardIssueSchema",
    "CardReadSchema",
    "CardTypeCreateSchema",
    "CardTypeReadSchema",
    "CardTypeUpdateSchema",
    "CoachCreateSchema",
    "CoachReadSchema",
    "CoachUpdateSchema",
    "MemberCreateSchema",
    "MemberReadSchema",
    "MemberUpdateSchema",
]
