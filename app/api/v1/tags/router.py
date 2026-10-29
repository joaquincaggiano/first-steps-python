from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.tags.repository import TagRepository
from app.api.v1.tags.schemas import TagCreate, TagPublic
from app.core.db import get_db
from app.core.security import get_current_user


router = APIRouter(prefix="/tags", tags=["tags"])


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
