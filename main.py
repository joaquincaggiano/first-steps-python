from fastapi import Body, FastAPI, HTTPException, Query

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
def create_post(post: dict = Body(...)):
    if "title" not in post or "content" not in post:
        return {"error": "El título y contenido son requeridos"}

    if not str(post["title"]).strip():
        return {"error": "El título no puede estar vacío"}
    if not str(post["content"]).strip():
        return {"error": "El contenido no puede estar vacío"}

    new_id = max(post["id"] for post in BLOG_POSTS) + 1 if BLOG_POSTS else 1

    new_post = {"id": new_id, **post}

    BLOG_POSTS.append(new_post)
    return {"message": "Post creado", "data": new_post}


@app.put("/posts/{post_id}")
def update_post(post_id: int, data: dict = Body(...)):
    for post in BLOG_POSTS:
        if post["id"] == post_id:
            post_updated = {**post, **data}
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
