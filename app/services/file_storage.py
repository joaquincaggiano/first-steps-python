import os
import shutil
import uuid
from fastapi import HTTPException, UploadFile, status
from app.core.config import MEDIA_DIR, MEDIA_URL

MIMES_ALLOWED = ["image/jpeg", "image/png"]


def ensure_media_dir():
    os.makedirs(MEDIA_DIR, exist_ok=True)


def save_uploaded_file(file: UploadFile) -> dict:
    if file.content_type not in MIMES_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de archivo no permitido")

    ensure_media_dir()

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1]  # accedemos a la extensión del archivo
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(MEDIA_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": filename,
        "content_type": file.content_type,
        "url": f"{MEDIA_URL}/{filename}"
    }
