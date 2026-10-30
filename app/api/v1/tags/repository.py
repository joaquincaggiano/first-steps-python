from math import ceil
from typing import Literal, Optional, Sequence, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.tags.schemas import TagPublic
from app.models.tag import TagORM
from app.services.pagination import paginate_query


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_tag(self, tag_id: int) -> TagORM:
        tag_obj = self.db.get(TagORM, tag_id)

        if not tag_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag no encontrado")

        return tag_obj

    def list_tags(
        self,
        search: Optional[str],
        order_by: Literal["id", "name"] = "id",
        direction: Literal["asc", "desc"] = "asc",
        page: int = 1,
        per_page: int = 10,
    ):
        results = select(TagORM)

        if search:
            results = results.where(func.lower(
                TagORM.name).ilike(f"%{search.lower()}%"))

        allowed_order = {
            "id": TagORM.id,
            "name": func.lower(TagORM.name),
        }
        result = paginate_query(
            db=self.db,
            model=TagORM,
            base_query=results,
            page=page,
            per_page=per_page,
            order_by=order_by,
            direction=direction,
            allowed_order=allowed_order
        )

        # model_validate is used to convert the SQLAlchemy model to the Pydantic model
        result["items"] = [TagPublic.model_validate(
            item) for item in result["items"]]

        return result

    def create_tag(self, name: str):
        normalized_name = name.strip().lower()

        tag_obj = self.db.execute(
            select(TagORM).where(TagORM.name.ilike(normalized_name))
        ).scalar_one_or_none()

        if not tag_obj:
            tag_obj = TagORM(name=normalized_name)
            self.db.add(tag_obj)
            self.db.flush()

        return tag_obj

    def update_tag(self, tag_id: int, name: str) -> TagORM:
        tag_obj = self.get_tag(tag_id)
        normalized_name = name.strip().lower()

        existing = self.db.execute(
            select(TagORM).where(
                TagORM.name.ilike(normalized_name),
                TagORM.id != tag_id,
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un tag con ese nombre",
            )

        tag_obj.name = normalized_name
        self.db.flush()

        return tag_obj

    def delete_tag(self, tag_id: int) -> None:
        tag_obj = self.get_tag(tag_id)
        self.db.delete(tag_obj)
        return
