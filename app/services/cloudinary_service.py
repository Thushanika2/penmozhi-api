import logging

import cloudinary
import cloudinary.uploader
from flask import current_app

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-m4v",
}
MAX_VIDEO_BYTES = 200 * 1024 * 1024  # 200 MB


def init_cloudinary(app) -> None:
    """Configure Cloudinary from app config / environment (no-op if unset)."""
    cloud_name = app.config.get("CLOUDINARY_CLOUD_NAME")
    api_key = app.config.get("CLOUDINARY_API_KEY")
    api_secret = app.config.get("CLOUDINARY_API_SECRET")

    if not (cloud_name and api_key and api_secret):
        logger.warning(
            "Cloudinary is not fully configured "
            "(CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET). "
            "Education video upload will be unavailable."
        )
        return

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    logger.info("Cloudinary configured for cloud_name=%s", cloud_name)


def cloudinary_configured() -> bool:
    return bool(
        current_app.config.get("CLOUDINARY_CLOUD_NAME")
        and current_app.config.get("CLOUDINARY_API_KEY")
        and current_app.config.get("CLOUDINARY_API_SECRET")
    )


def validate_video_file(file_storage) -> str | None:
    """Return an error message if invalid, otherwise None."""
    if file_storage is None or not getattr(file_storage, "filename", None):
        return "A video file is required."

    filename = str(file_storage.filename).strip()
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
        return "Video must be an mp4, mov, webm, or m4v file."

    mime = (getattr(file_storage, "mimetype", None) or "").lower().strip()
    if mime and mime not in ALLOWED_VIDEO_MIME_TYPES and not mime.startswith("video/"):
        return "Unsupported video content type."

    # Content-Length may be unavailable; try seeking for size when possible.
    try:
        stream = file_storage.stream
        pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(pos)
        if size > MAX_VIDEO_BYTES:
            return "Video must be 200 MB or smaller."
    except Exception:
        pass

    return None


def upload_education_video(file_storage, *, folder: str = "penmozhi/education") -> dict:
    """
    Upload a video to Cloudinary using chunked upload_large.
    Returns dict with secure_url and public_id.
    """
    if not cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured.")

    result = cloudinary.uploader.upload_large(
        file_storage,
        resource_type="video",
        folder=folder,
        chunk_size=6_000_000,
    )
    return {
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }


def destroy_education_video(public_id: str) -> None:
    if not public_id:
        return
    if not cloudinary_configured():
        logger.warning("Skipping Cloudinary destroy; credentials not configured.")
        return
    cloudinary.uploader.destroy(public_id, resource_type="video")
