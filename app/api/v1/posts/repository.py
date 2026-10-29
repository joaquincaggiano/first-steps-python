from math import ceil
from typing import List, Literal, Optional, Sequence, Tuple
from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.api.v1.posts.schemas import Author, PostCreate, PostPublic
from app.models import PostORM, AuthorORM, TagORM
from app.services.pagination import paginate_query


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
    ) -> dict:
        results = select(PostORM)

        if query:
            results = results.where(PostORM.title.ilike(f"%{query}%"))

        allowed_order = {
            "id": PostORM.id,
            "title": func.lower(PostORM.title),
        }

        result = paginate_query(
            db=self.db,
            model=PostORM,
            base_query=results,
            page=page,
            per_page=per_page,
            order_by=order_by,
            direction=direction,
            allowed_order=allowed_order
        )

        # model_validate is used to convert the SQLAlchemy model to the Pydantic model
        result["items"] = [PostPublic.model_validate(
            item) for item in result["items"]]

        return result

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
        normalized_name = name.strip().lower()

        tag_obj = self.db.execute(
            select(TagORM).where(TagORM.name.ilike(normalized_name))
        ).scalar_one_or_none()

        if not tag_obj:
            tag_obj = TagORM(name=normalized_name)
            self.db.add(tag_obj)
            self.db.flush()

        return tag_obj

    def create_post(
        self,
        data: PostCreate,
        author: Author,
        image_url: Optional[str] = None
    ) -> PostORM:
        author_obj = self.ensure_author(author.name, author.email)

        new_post = PostORM(
            title=data.title,
            content=data.content,
            author=author_obj,
            image_url=image_url,
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

        return post

    def delete_post(self, post: PostORM) -> None:
        self.db.delete(post)
