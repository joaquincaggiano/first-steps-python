import uuid
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.core.config import MEDIA_DIR, MEDIA_URL
from app.services.file_storage import save_uploaded_file

router = APIRouter(prefix="/uploads", tags=["uploads"])


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
    saved = save_uploaded_file(file)

    return saved
