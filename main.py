from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Literal, Optional, Union

app = FastAPI(title="Mini Blog")


BLOG_POSTS = [
    {
        "id": 1,
        "title": "Introducción a Python",
        "content": "Aprende los conceptos básicos de Python."
    },
    {
        "id": 2,
        "title": "¿Qué es una API?",
        "content": "Las APIs permiten la comunicación entre aplicaciones."
    },
    {
        "id": 3,
        "title": "Primeros pasos con JavaScript",
        "content": "Cómo comenzar a programar con JavaScript."
    },
    {
        "id": 4,
        "title": "¿Qué es Git y para qué sirve?",
        "content": "Git es una herramienta para control de versiones."
    },
    {
        "id": 5,
        "title": "Ventajas de usar frameworks",
        "content": "Un framework acelera el desarrollo y facilita el mantenimiento."
    },
    {
        "id": 6,
        "title": "Bases de datos relacionales",
        "content": "Descubre cómo funcionan las bases de datos SQL."
    },
    {
        "id": 7,
        "title": "¿Por qué aprender TypeScript?",
        "content": "TypeScript ayuda a evitar errores en JavaScript."
    },
    {
        "id": 8,
        "title": "Automatización con scripts",
        "content": "Los scripts pueden automatizar tareas repetitivas."
    },
    {
        "id": 9,
        "title": "Introducción a FastAPI",
        "content": "FastAPI es un framework moderno para APIs en Python."
    },
    {
        "id": 10,
        "title": "Diferencias entre frontend y backend",
        "content": "Conoce qué distingue al desarrollo frontend del backend."
    }
]

FORBIDDEN_WORDS = ["spam", "banned", "badword", "xxx", "gambling"]


class Tag(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=30,
        description="Nombre de la etiqueta"
    )


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


class PostSummary(BaseModel):
    id: int
    title: str


@app.get("/")
def home():
    return {
        "message": "Bienvenidos a mi Mini Blog"
    }


@app.get(
    "/posts",
    response_model=List[PostPublic],
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
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Número de resultados (1-50)"
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Número de resultados a saltar"
    ),
    order_by: Literal["id", "title"] = Query(
        default="id",
        description="Ordenar por id o título"
    ),
    direction: Literal["asc", "desc"] = Query(
        default="asc",
        description="Dirección ascendente o descendente"
    )
):
    results = BLOG_POSTS

    if query:
        results = [post for post in results if query.lower()
                   in post["title"].lower()]

    results = sorted(
        results, key=lambda post: post[order_by], reverse=(direction == "desc"))

    return results[offset:offset+limit]


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
    )
):
    for post in BLOG_POSTS:
        if post["id"] == post_id:
            if include_content:
                return post
            else:
                return {
                    "id": post["id"],
                    "title": post["title"]
                }

    raise HTTPException(
        status_code=404, detail=f"Post {post_id} no encontrado")


@app.post(
    "/posts",
    response_model=PostPublic,
    response_description="Post creado con éxito"
)
def create_post(post: PostCreate):
    new_id = max(post["id"] for post in BLOG_POSTS) + 1 if BLOG_POSTS else 1

    new_post = {
        "id": new_id,
        **post.model_dump(),
        "tags": [tag.model_dump() for tag in post.tags],
        "author": post.author.model_dump() if post.author else None
    }

    BLOG_POSTS.append(new_post)
    return new_post


@app.put(
    "/posts/{post_id}",
    response_model=PostPublic,
    response_description="Post actualizado con éxito"
)
def update_post(post_id: int, data: PostUpdate):
    for post in BLOG_POSTS:
        if post["id"] == post_id:
            post_updated = {**post, **data.model_dump(exclude_unset=True)}
            index = BLOG_POSTS.index(post)
            BLOG_POSTS[index] = post_updated
            return post_updated

    raise HTTPException(
        status_code=404, detail=f"Post {post_id} no encontrado")


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    for i, post in enumerate(BLOG_POSTS):
        if post["id"] == post_id:
            BLOG_POSTS.pop(i)
            return

    raise HTTPException(
        status_code=404, detail=f"Post {post_id} no encontrado")
