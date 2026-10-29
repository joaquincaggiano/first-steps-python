from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import TagORM


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

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
