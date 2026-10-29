from math import ceil
from typing import Any, Dict, Literal, Optional, Type
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import Base

DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100


def sanitize_pagination(page: int = 1, per_page: int = DEFAULT_PER_PAGE):
    page = max(1, int(page or 1))
    per_page = min(MAX_PER_PAGE, max(1, int(per_page or DEFAULT_PER_PAGE)))

    return page, per_page


def paginate_query(
    db: Session,
    model: Type[Base],
    base_query=None,
    page: int = 1,
    per_page: int = DEFAULT_PER_PAGE,
    order_by: Optional[str] = None,
    direction: Literal["asc", "desc"] = "asc",
    allowed_order: Optional[Dict[str, Any]] = None,
):
    page, per_page = sanitize_pagination(page, per_page)
    # SQLAlchemy Select has no boolean value — use `is not None`, not `if base_query`
    query = base_query if base_query is not None else select(model)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    if total == 0:
        return {
            "page": page,
            "per_page": per_page,
            "total": 0,
            "total_pages": 0,
            "has_prev": False,
            "has_next": False,
            "order_by": order_by,
            "direction": direction,
            "items": [],
        }

    if allowed_order and order_by:
        col = allowed_order.get(order_by, allowed_order.get("id"))
        if col is not None:
            query = query.order_by(
                col.desc() if direction == "desc" else col.asc()
            )

    items = db.execute(query.offset(
        (page - 1) * per_page).limit(per_page)).scalars().all()

    total_pages = ceil(total / per_page)

    has_prev = page > 1
    has_next = page < total_pages if total_pages > 0 else False

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
        "order_by": order_by,
        "direction": direction,
        "items": items,
    }
