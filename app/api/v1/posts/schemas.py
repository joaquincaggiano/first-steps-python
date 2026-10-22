from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
