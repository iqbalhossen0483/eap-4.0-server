import asyncio
import io
import cloudinary.uploader
from pathlib import Path
from fastapi import HTTPException, UploadFile

try:
    import magic as magic

    _MAGIC_AVAILABLE = True
except ImportError:
    magic = None  # type: ignore[assignment]
    _MAGIC_AVAILABLE = False

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


async def upload_avatar(file: UploadFile, user_id: str) -> str:
    """Validate an image upload, store it in Cloudinary, and return the URL."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="Image exceeds 5 MB limit")

    if _MAGIC_AVAILABLE:
        assert magic is not None
        loop = asyncio.get_event_loop()
        mime = await loop.run_in_executor(None, magic.from_buffer, content[:2048], True)
        if mime not in ALLOWED_MIMES:
            raise HTTPException(
                status_code=422, detail="File content is not a valid image"
            )

    def _upload():
        # One avatar per user — overwrite the previous one at a stable public_id.
        return cloudinary.uploader.upload(
            io.BytesIO(content),
            public_id=f"avatars/{user_id}",
            resource_type="image",
            overwrite=True,
            invalidate=True,
        )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _upload)
    return result["secure_url"]
