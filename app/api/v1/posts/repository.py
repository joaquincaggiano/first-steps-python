from math import ceil
from typing import List, Literal, Optional, Sequence, Tuple
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.api.v1.posts.schemas import PostCreate
from app.models import PostORM, AuthorORM, TagORM


class PostRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, post_id: int) -> Optional[PostORM]:
        # Si post_id no fuera un primary key, podemos buscarlo así:
        # post__found = select(PostORM).where(PostORM.id == post_id).first()
        # post = db.execute(post_found).scalar_one_or_none()
        post = self.db.get(PostORM, post_id)
        return post

    def search(
        self,
        query: Optional[str],
        order_by: Literal["id", "title"],
        direction: Literal["asc", "desc"],
        page: int,
        per_page: int,
    ) -> Tuple[int, Sequence[PostORM]]:
        results = select(PostORM)

        if query:
            results = results.where(PostORM.title.ilike(f"%{query}%"))

        total = self.db.scalar(select(func.count()).select_from(
            results.subquery())) or 0

        if total == 0:
            return 0, []

        total_pages = ceil(total / per_page)

        current_page = min(page, max(1, total_pages))

        order_col = PostORM.id if order_by == "id" else func.lower(
            PostORM.title)

        results = results.order_by(
            order_col.asc() if direction == "asc" else order_col.desc())

        start = (current_page - 1) * per_page
        items = self.db.execute(
            results.limit(per_page).offset(start)
        ).scalars().all()

        return total, items

    def by_tags(self, tags: List[str]) -> Sequence[PostORM]:
        normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]

        if not normalized_tags:
            return []

        posts = self.db.execute(
            select(PostORM).options(
                selectinload(PostORM.tags),
                joinedload(PostORM.author),
            ).where(PostORM.tags.any(func.lower(TagORM.name).in_(normalized_tags)))
            .order_by(PostORM.id.asc())
        ).scalars().all()

        return posts

    def ensure_author(self, name: str, email: EmailStr) -> AuthorORM:
        author_obj = self.db.execute(
            select(AuthorORM).where(AuthorORM.email == email)
        ).scalar_one_or_none()

        if not author_obj:
            author_obj = AuthorORM(name=name,
                                   email=email)
            self.db.add(author_obj)
            self.db.flush()  # Guarda el objeto en la base de datos pero no lo commit

        return author_obj

    def ensure_tag(self, name: str) -> TagORM:
        tag_obj = self.db.execute(
            select(TagORM).where(TagORM.name.ilike(name))
        ).scalar_one_or_none()

        if not tag_obj:
            tag_obj = TagORM(name=name)
            self.db.add(tag_obj)
            self.db.flush()

        return tag_obj

    def create_post(self, data: PostCreate) -> PostORM:
        author_obj = self.ensure_author(
            data.author.name, data.author.email) if data.author else None
        # tag_objs = [self.ensure_tag(tag.name) for tag in data.tags]

        new_post = PostORM(
            title=data.title,
            content=data.content,
            author=author_obj,
        )

        for tag in data.tags:
            tag_obj = self.ensure_tag(tag.name)
            new_post.tags.append(tag_obj)

        self.db.add(new_post)
        self.db.flush()
        self.db.refresh(new_post)
        return new_post

    def update_post(self, post: PostORM, updates: dict) -> PostORM:
        for key, value in updates.items():
            setattr(post, key, value)

        self.db.add(post)
        self.db.refresh(post)
        return post

    def delete_post(self, post: PostORM) -> None:
        self.db.delete(post)
