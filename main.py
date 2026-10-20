from datetime import datetime, timezone
import os
from math import ceil
from fastapi import Depends, FastAPI, HTTPException, Query, Path, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import List, Literal, Optional, Union
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, create_engine, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Mapped, joinedload, mapped_column, relationship, selectinload, sessionmaker, Session, DeclarativeBase
from dotenv import load_dotenv


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./blog.db")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    **engine_kwargs
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,  # Deprecado en SQLAlchemy 2.0
    class_=Session
)


class Base(DeclarativeBase):
    pass


post_tags = Table(
    "post_tags",
    Base.metadata,
    Column(
        "post_id",
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "tag_id",
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class AuthorORM(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[EmailStr] = mapped_column(
        String(100), unique=True, index=True)

    posts: Mapped[List[PostORM]] = relationship(back_populates="author")


class TagORM(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    posts: Mapped[List["PostORM"]] = relationship(
        secondary=post_tags,
        back_populates="tags",
        lazy="selectin"
    )


class PostORM(Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("title", name="unique_post_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Optional[AuthorORM]] = relationship(back_populates="posts")

    tags: Mapped[List["TagORM"]] = relationship(
        secondary=post_tags,
        back_populates="posts",
        lazy="selectin",
        passive_deletes=True
    )


Base.metadata.create_all(bind=engine)  # Dev


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Mini Blog")

FORBIDDEN_WORDS = ["spam", "banned", "badword", "xxx", "gambling"]


class Tag(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Nombre de la etiqueta"
    )

    # Para que pueda validar objetos de tipo TagORM
    model_config = ConfigDict(from_attributes=True)


class Author(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Nombre del autor"
    )
    email: EmailStr = Field(
        ...,
        description="Email del usuario",
        examples=["joaquincaggiano@gmail.com"]
    )

    model_config = ConfigDict(from_attributes=True)


class PostBase(BaseModel):
    title: str
    content: str
    tags: Optional[List[Tag]] = Field(default_factory=list)
    author: Optional[Author] = None


class PostCreate(BaseModel):
    title: str = Field(
        ...,  # Hace que sea obligatorio
        min_length=3,
        max_length=100,
        description="Título del post",
        examples=["Mi primer post con FastAPI"]
    )
    content: Optional[str] = Field(
        default="",
        min_length=10,
        description="Contenido del post",
        examples=["Este es el contenido de mi primer post"]
    )
    tags: List[Tag] = Field(default_factory=list)
    author: Optional[Author] = None

    @field_validator("title")  # Evalua el campo title
    @classmethod  # Para que se pueda usar en la clase
    def forbidden_title(cls, value: str) -> str:
        for word in FORBIDDEN_WORDS:
            if word in value.lower():
                raise ValueError(
                    f"El título no puede contener la palabra {word}")
        return value


class PostUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Título del post",
        examples=["Mi primer post con FastAPI"]
    )
    content: Optional[str] = Field(
        default=None,
        min_length=10,
        description="Contenido del post",
        examples=["Este es el contenido de mi primer post"]
    )

    @field_validator("title")  # Evalua el campo title
    @classmethod  # Para que se pueda usar en la clase
    def forbidden_title(cls, value: str) -> str:
        for word in FORBIDDEN_WORDS:
            if word in value.lower():
                raise ValueError(
                    f"El título no puede contener la palabra {word}")
        return value


class PostPublic(PostBase):
    id: int
    # Para que pueda validar objetos de tipo PostORM
    model_config = ConfigDict(from_attributes=True)


class PostSummary(BaseModel):
    id: int
    title: str

    # Para que pueda validar objetos de tipo PostORM
    model_config = ConfigDict(from_attributes=True)


class PaginatedPost(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_prev: bool
    has_next: bool
    order_by: Literal["id", "title"]
    direction: Literal["asc", "desc"]
    search: Optional[str] = None
    items: List[PostPublic]


@app.get(
    "/posts",
    response_model=PaginatedPost,
    response_model_exclude_none=True
)
def list_posts(
    query: Optional[str] = Query(
        default=None,
        description="Texto para buscar por el título",
        alias="search",  # A nivel público el usuario ve search, a nivel de código será query
        min_length=3,
        max_length=50,
        pattern=r"^[\w\sáéíóúÁÉÍÓÚüÜ-]+$"
    ),
    per_page: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Número de resultados (1-50)"
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Número de página"
    ),
    order_by: Literal["id", "title"] = Query(
        default="id",
        description="Ordenar por id o título"
    ),
    direction: Literal["asc", "desc"] = Query(
        default="asc",
        description="Dirección ascendente o descendente"
    ),
    db: Session = Depends(get_db)
):
    # results = BLOG_POSTS
    results = select(PostORM)

    # if query:
    #     results = [post for post in results if query.lower()
    #                in post["title"].lower()]
    if query:
        results = results.where(PostORM.title.ilike(f"%{query}%"))

    # total = len(results)
    total = db.scalar(select(func.count()).select_from(
        results.subquery())) or 0
    total_pages = ceil(total / per_page) if total > 0 else 0

    # if total_pages == 0:
    #     current_page = 1
    # else:
    #     current_page = min(page, total_pages)
    current_page = 1 if total_pages == 0 else min(page, total_pages)

    if order_by == "id":
        order_col = PostORM.id
    else:
        order_col = func.lower(PostORM.title)

    # results = sorted(
    #     results, key=lambda post: post[order_by], reverse=(direction == "desc"))
    results = results.order_by(
        order_col.asc() if direction == "asc" else order_col.desc())

    # if total_pages == 0:
    #     items = []
    # else:
    #     start = (current_page - 1) * per_page
    #     end = start + per_page
    #     # Convierte los posts a PostPublic
    #     items = [
    #         PostPublic.model_validate(post)
    #         for post in results[start:end]
    #     ]
    if total_pages == 0:
        items: List[PostPublic] = []
    else:
        start = (current_page - 1) * per_page
        rows = db.execute(
            results.limit(per_page).offset(start)
        ).scalars().all()
        items = [PostPublic.model_validate(post) for post in rows]

    has_prev = current_page > 1
    has_next = current_page < total_pages if total_pages > 0 else False

    return PaginatedPost(
        page=current_page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        order_by=order_by,
        direction=direction,
        search=query,
        items=items
    )


@app.get("/posts/by-tags", response_model=List[PostPublic])
def get_posts_by_tags(
    tags: List[str] = Query(
        ...,
        min_length=1,
        description="Una o más etiquetas. Ej: ?tags=python&tags=fastapi"
    ),
    db: Session = Depends(get_db)
):
    normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]

    if not normalized_tags:
        return []

    posts = db.execute(
        select(PostORM).options(
            selectinload(PostORM.tags),
            joinedload(PostORM.author),
        ).where(PostORM.tags.any(func.lower(TagORM.name).in_(normalized_tags)))
        .order_by(PostORM.id.asc())
    ).scalars().all()

    return posts

    # tags_lower = [tag.lower() for tag in tags]

    # return [
    #     post for post in BLOG_POSTS
    #     if any(tag["name"].lower() in tags_lower for tag in post.get("tags", []))
    # ]


@app.get(
    "/posts/{post_id}",
    response_model=Union[PostPublic, PostSummary],
    response_description="Post encontrado",
    response_model_exclude_none=True
)
def get_post(
    post_id: int = Path(
        ...,
        ge=1,
        title="ID del Post",
        description="Identificador entero del post. Debe ser mayor a 1",
        example=1
    ),
    include_content: bool = Query(
        default=True, description="Incluir o no el contenido del blog"
    ),
    db: Session = Depends(get_db)
):
    # Si post_id no fuera un primary key, podemos buscarlo así:
    # post__found = select(PostORM).where(PostORM.id == post_id).first()
    # post = db.execute(post_found).scalar_one_or_none()
    post = db.get(PostORM, post_id)

    if not post:
        raise HTTPException(
            status_code=404, detail=f"Post {post_id} no encontrado")

    if include_content:
        return PostPublic.model_validate(post, from_attributes=True)

    return PostSummary.model_validate(post, from_attributes=True)

    # for post in BLOG_POSTS:
    #     if post["id"] == post_id:
    #         if include_content:
    #             return post
    #         else:
    #             return {
    #                 "id": post["id"],
    #                 "title": post["title"]
    #             }

    # raise HTTPException(
    #     status_code=404, detail=f"Post {post_id} no encontrado")


@app.post(
    "/posts",
    response_model=PostPublic,
    response_description="Post creado con éxito",
    status_code=status.HTTP_201_CREATED
)
def create_post(post: PostCreate, db: Session = Depends(get_db)):
    author_obj = None

    if post.author:
        author_obj = db.execute(
            select(AuthorORM).where(AuthorORM.email == post.author.email)
        ).scalar_one_or_none()

        if not author_obj:
            author_obj = AuthorORM(name=post.author.name,
                                   email=post.author.email)
            db.add(author_obj)
            db.flush()  # Guarda el objeto en la base de datos pero no lo commit

    new_post = PostORM(
        title=post.title,
        content=post.content,
        author=author_obj
    )

    for tag in post.tags:
        tag_obj = db.execute(
            select(TagORM).where(TagORM.name.ilike(tag.name))
        ).scalar_one_or_none()
        if not tag_obj:
            tag_obj = TagORM(name=tag.name)
            db.add(tag_obj)
            db.flush()
        new_post.tags.append(tag_obj)

    try:
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        return new_post
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El título ya existe")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear el post")
    # new_id = max(post["id"] for post in BLOG_POSTS) + 1 if BLOG_POSTS else 1

    # new_post = {
    #     "id": new_id,
    #     **post.model_dump(),
    #     "tags": [tag.model_dump() for tag in post.tags],
    #     "author": post.author.model_dump() if post.author else None
    # }

    # BLOG_POSTS.append(new_post)
    # return new_post


@app.put(
    "/posts/{post_id}",
    response_model=PostPublic,
    response_description="Post actualizado con éxito"
)
def update_post(post_id: int, data: PostUpdate, db: Session = Depends(get_db)):
    post = db.get(PostORM, post_id)

    if not post:
        raise HTTPException(
            status_code=404, detail=f"Post {post_id} no encontrado")

    # exclude_unset evita que en la respuesta aparezca null en campos que no se envian
    updates = data.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(post, key, value)

    try:
        db.commit()
        db.refresh(post)
        return post
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error al actualizar el post")

    # for post in BLOG_POSTS:
    #     if post["id"] == post_id:
    #         post_updated = {**post, **data.model_dump(exclude_unset=True)}
    #         index = BLOG_POSTS.index(post)
    #         BLOG_POSTS[index] = post_updated
    #         return post_updated

    # raise HTTPException(
    #     status_code=404, detail=f"Post {post_id} no encontrado")


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(PostORM, post_id)

    if not post:
        raise HTTPException(
            status_code=404, detail=f"Post {post_id} no encontrado")

    try:
        db.delete(post)
        db.commit()
        return
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500, detail="Error al eliminar el post")

        # for i, post in enumerate(BLOG_POSTS):
        #     if post["id"] == post_id:
        #         BLOG_POSTS.pop(i)
        #         return

        # raise HTTPException(
        #     status_code=404, detail=f"Post {post_id} no encontrado")
