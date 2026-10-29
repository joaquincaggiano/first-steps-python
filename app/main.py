import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.core.config import MEDIA_DIR, MEDIA_URL
from app.core.db import Base, engine
from app.api.v1.posts.router import router as posts_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.uploads.router import router as uploads_router
from app.api.v1.tags.router import router as tags_router


load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Blog")

    # Crea las tablas en la base de datos
    Base.metadata.create_all(bind=engine)  # Dev

    # Incluye las rutas de la API
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(posts_router)
    app.include_router(uploads_router)
    app.include_router(tags_router)

    os.makedirs(MEDIA_DIR, exist_ok=True)
    app.mount(MEDIA_URL, StaticFiles(directory=MEDIA_DIR), name="media")

    return app


app = create_app()
