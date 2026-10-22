from math import ceil
from typing import List, Literal, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.posts.repository import PostRepository
from app.api.v1.posts.schemas import Author, PaginatedPost, PostCreate, PostPublic, PostSummary, PostUpdate
from app.core.db import get_db
from app.core.security import get_current_user

# tags sirve para los metadatos de la API
router = APIRouter(prefix="/posts", tags=["posts"])


@router.get(
    "",
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
    repository = PostRepository(db)

    total, items = repository.search(
        query=query,
        order_by=order_by,
        direction=direction,
        page=page,
        per_page=per_page
    )

    total_pages = ceil(total / per_page) if total > 0 else 0
    current_page = min(page, max(1, total_pages))
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
        items=[PostPublic.model_validate(item) for item in items]
    )


@router.get("/by-tags", response_model=List[PostPublic])
def get_posts_by_tags(
    tags: List[str] = Query(
        ...,
        min_length=1,
        description="Una o más etiquetas. Ej: ?tags=python&tags=fastapi"
    ),
    db: Session = Depends(get_db)
):
    repository = PostRepository(db)
    posts = repository.by_tags(tags)

    return [PostPublic.model_validate(post) for post in posts]


@router.get(
    "/{post_id}",
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
        examples=[1]
    ),
    include_content: bool = Query(
        default=True, description="Incluir o no el contenido del blog"
    ),
    db: Session = Depends(get_db)
):
    repository = PostRepository(db)
    post = repository.get(post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} no encontrado")

    return (
        PostPublic.model_validate(post, from_attributes=True)
        if include_content
        else PostSummary.model_validate(post, from_attributes=True)
    )


@router.post(
    "",
    response_model=PostPublic,
    response_description="Post creado con éxito",
    status_code=status.HTTP_201_CREATED
)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    repository = PostRepository(db)
    author = Author(name=user["username"], email=user["email"])

    try:
        new_post = repository.create_post(post, author=author)
        db.commit()
        db.refresh(new_post)
        return new_post
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El título ya existe")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el post")


@router.put(
    "/{post_id}",
    response_model=PostPublic,
    response_description="Post actualizado con éxito"
)
def update_post(
    post_id: int,
    data: PostUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    repository = PostRepository(db)
    post = repository.get(post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} no encontrado")

    # exclude_unset evita que en la respuesta aparezca null en campos que no se envian
    updates = data.model_dump(exclude_unset=True)

    try:
        repository.update_post(post, updates)
        db.commit()
        db.refresh(post)
        return post
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el post")


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    repository = PostRepository(db)
    post = repository.get(post_id)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Post {post_id} no encontrado")

    try:
        repository.delete_post(post)
        db.commit()
        return
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar el post")
