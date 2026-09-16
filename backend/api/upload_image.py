"""
Image Upload API — Handle dispensing defect image uploads.

Receives an uploaded image, stores it in Supabase Storage,
and associates it with the current session.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

router = APIRouter()


class UploadResponse(BaseModel):
    session_id: str
    image_url: str
    message: str


@router.post("/upload-image", response_model=UploadResponse)
async def upload_image(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload a dispensing defect image for a session.

    TODO:
    - Validate file type (JPEG, PNG)
    - Upload to Supabase Storage
    - Save image URL/path to session record
    - Return the public URL
    """
    if file.content_type not in ("image/jpeg", "image/png"):
        raise HTTPException(status_code=400, detail="Only JPEG and PNG images are accepted.")

    return UploadResponse(
        session_id=session_id,
        image_url="[Placeholder] Not yet stored.",
        message=f"Image '{file.filename}' received (upload not yet implemented).",
    )
