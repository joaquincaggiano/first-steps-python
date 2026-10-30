from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.common.schemas import PaginatedResponse
from app.api.v1.tags.repository import TagRepository
from app.api.v1.tags.schemas import TagCreate, TagPublic, TagUpdate
from app.core.db import get_db
from app.core.security import get_current_user


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "/",
    response_model=PaginatedResponse[TagPublic],
    response_description="Tags listadas correctamente",
    status_code=status.HTTP_200_OK
)
def list_tags(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    order_by: Literal["id", "name"] = Query(default="id"),
    direction: Literal["asc", "desc"] = Query(default="asc"),
    search: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    repository = TagRepository(db)
    result = repository.list_tags(
        search=search,
        order_by=order_by,
        direction=direction,
        page=page,
        per_page=per_page
    )
    return PaginatedResponse[TagPublic].model_validate(result)


@router.post(
    "/",
    response_model=TagPublic,
    response_description="Tag creado correctamente",
    status_code=status.HTTP_201_CREATED
)
def create_tag(
    tag: TagCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    try:
        repository = TagRepository(db)
        new_tag = repository.create_tag(tag.name)
        db.commit()
        db.refresh(new_tag)
        return new_tag
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el tag"
        )


@router.put(
    "/{tag_id}",
    response_model=TagPublic,
    response_description="Tag actualizado correctamente",
    status_code=status.HTTP_200_OK
)
def update_tag(
    tag_id: int,
    tag: TagUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    try:
        repository = TagRepository(db)
        updated_tag = repository.update_tag(tag_id, tag.name)
        db.commit()
        return TagPublic.model_validate(updated_tag)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el tag"
        )


@router.delete(
    "/{tag_id}",
    response_description="Tag eliminado correctamente",
    status_code=status.HTTP_200_OK
)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    try:
        repository = TagRepository(db)
        repository.delete_tag(tag_id)
        db.commit()
        return {"message": "Tag eliminado correctamente"}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar el tag"
        )


@router.get(
    "/most-popular",
    response_model=TagPublic,
    response_description="Tag más popular",
    status_code=status.HTTP_200_OK
)
def most_popular(
    db: Session = Depends(get_db)
):
    repository = TagRepository(db)
    result = repository.most_popular()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el tag más popular"
        )
    return TagPublic.model_validate(result)
