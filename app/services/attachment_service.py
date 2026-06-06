import asyncio
import io
import cloudinary.uploader
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile

from app.models.attachment import Attachment

try:
    import magic as magic

    _MAGIC_AVAILABLE = True
except ImportError:
    magic = None  # type: ignore[assignment]
    _MAGIC_AVAILABLE = False

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".zip",
    ".txt",
}
ALLOWED_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
    "application/zip",
    "text/plain",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


async def upload_attachment(
    file: UploadFile, task_id: str, uploader_id: str
) -> Attachment:
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="File type not allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="File exceeds 10 MB limit")

    if _MAGIC_AVAILABLE:
        assert magic is not None
        loop = asyncio.get_event_loop()
        mime = await loop.run_in_executor(None, magic.from_buffer, content[:2048], True)
        if mime not in ALLOWED_MIMES:
            raise HTTPException(
                status_code=422, detail="File content does not match allowed types"
            )

    public_id = str(uuid4())

    def _upload():
        return cloudinary.uploader.upload(
            io.BytesIO(content),
            public_id=f"attachments/{public_id}",
            resource_type="auto",
            use_filename=False,
        )

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _upload)

    return Attachment(
        id=public_id,
        original_filename=file.filename,
        cloudinary_url=result["secure_url"],
        cloudinary_public_id=result["public_id"],
        file_size=len(content),
        task_id=task_id,
        uploaded_by=uploader_id,
    )


async def delete_attachment_from_cloud(attachment: Attachment) -> None:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: cloudinary.uploader.destroy(
            attachment.cloudinary_public_id, resource_type="raw"
        ),
    )
