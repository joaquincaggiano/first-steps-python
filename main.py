from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Mini Blog")


BLOG_POSTS = [
    {
        "id": 1,
        "title": "Mi primer post",
        "content": "Este es el contenido de mi primer post"
    },
    {
        "id": 2,
        "title": "Mi segundo post",
        "content": "Este es el contenido de mi segundo post"
    },
    {
        "id": 3,
        "title": "Mi tercer post",
        "content": "Este es el contenido de mi tercer post"
    }
]


class PostBase(BaseModel):
    title: str
    content: Optional[str] = ""


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


@app.get("/")
def home():
    return {
        "message": "Bienvenidos a mi Mini Blog"
    }


@app.get("/posts")
def list_posts(query: str | None = Query(default=None, description="Texto para buscar por el título")):
    if query:
        results = [post for post in BLOG_POSTS if query.lower()
                   in post["title"].lower()]
        # for post in BLOG_POSTS:
        #     if query.lower() in post["title"].lower():
        #         results.append(post)
        return {"data": results, "query": query}

    return {"data": BLOG_POSTS}


@app.get("/posts/{post_id}")
def get_post(post_id: int, include_content: bool = Query(default=True, description="Incluir o no el contenido del blog")):
    for post in BLOG_POSTS:
        if post["id"] == post_id:
            if include_content:
                return {"data": post}
            else:
                return {"data": {"id": post["id"], "title": post["title"]}}

    return {"error": "Post no encontrado"}


@app.post("/posts")
def create_post(post: PostCreate):
    new_id = max(post["id"] for post in BLOG_POSTS) + 1 if BLOG_POSTS else 1

    new_post = {"id": new_id, **post.model_dump()}

    BLOG_POSTS.append(new_post)
    return {"message": "Post creado", "data": new_post}


@app.put("/posts/{post_id}")
def update_post(post_id: int, data: PostUpdate):
    for post in BLOG_POSTS:
        if post["id"] == post_id:
            post_updated = {**post, **data.model_dump(exclude_unset=True)}
            index = BLOG_POSTS.index(post)
            BLOG_POSTS[index] = post_updated
            return {"message": f"Post {post["id"]} actualizado con éxito", "data": post_updated}

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
