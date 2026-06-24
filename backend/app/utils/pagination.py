"""分页工具。对照 Spring Data 的 ``Pageable`` / ``Page``。

通过查询参数 ``?page=1&per_page=20`` 控制；返回 items + meta。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import request
from sqlalchemy import func, select

from ..extensions import db

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


@dataclass
class PageParams:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


def parse_page_params(default_per_page: int = DEFAULT_PER_PAGE) -> PageParams:
    """从 ``request.args`` 解析 page / per_page，越界自动夹断。"""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", default_per_page))
    except (TypeError, ValueError):
        per_page = default_per_page
    per_page = max(1, min(MAX_PER_PAGE, per_page))
    return PageParams(page=page, per_page=per_page)


def paginate(stmt, serializer, params: PageParams | None = None) -> dict[str, Any]:
    """对 SQLAlchemy 2.0 ``select(...)`` 语句分页。

    Returns ``{"items": [...], "meta": {page, per_page, total, pages}}``。
    """
    params = params or parse_page_params()

    # 统计总数：用子查询包一层最稳，过滤/join 都不会被破坏
    total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.session.scalar(total_stmt) or 0

    rows = (
        db.session.execute(stmt.limit(params.limit).offset(params.offset)).scalars().all()
    )
    items = [serializer(r) for r in rows]

    pages = (total + params.per_page - 1) // params.per_page if total else 0
    return {
        "items": items,
        "meta": {
            "page": params.page,
            "per_page": params.per_page,
            "total": total,
            "pages": pages,
        },
    }
