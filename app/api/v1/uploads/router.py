import os
import shutil
import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter(prefix="/uploads", tags=["uploads"])

MEDIA_DIR = "app/media"


@router.post("/bytes")
async def upload_bytes(file: bytes = File(...)):
    return {
        "filename": f"archivo_{uuid.uuid4()}_subido",
        "size_bytes": len(file)
    }


@router.post("/file")
async def upload_file(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "content_type": file.content_type,
    }


@router.post("/save")
async def save_file(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de archivo no permitido")

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1] # accedemos a la extensión del archivo
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(MEDIA_DIR, filename)
    
    with open(file_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)
    
    return {
      "filename": filename,
      "content_type": file.content_type,
      "url": f"/media/{filename}"
    }