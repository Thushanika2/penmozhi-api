import logging
import time
from urllib.parse import urlparse

import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
import cloudinary.utils
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
EDUCATION_VIDEO_FOLDER = "penmozhi/education/videos"


def init_cloudinary(app) -> None:
    """Configure Cloudinary from app config / environment (no-op if unset)."""
    cloud_name = app.config.get("CLOUDINARY_CLOUD_NAME")
    api_key = app.config.get("CLOUDINARY_API_KEY")
    api_secret = app.config.get("CLOUDINARY_API_SECRET")

    logger.info(
        "Cloudinary configuration presence: cloud_name=%s api_key=%s api_secret=%s",
        bool(cloud_name),
        bool(api_key),
        bool(api_secret),
    )

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
    logger.info("Cloudinary SDK configured")


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
    Returns dict with secure_url, public_id, and thumbnail_url (first-frame jpg).
    """
    if not cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured.")

    result = cloudinary.uploader.upload_large(
        file_storage,
        resource_type="video",
        folder=folder,
        chunk_size=6_000_000,
    )
    public_id = result.get("public_id")
    secure_url = result.get("secure_url")
    thumbnail_url = None
    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME")
    if public_id and cloud_name:
        # Cloudinary auto thumbnail from the first frame.
        thumbnail_url = (
            f"https://res.cloudinary.com/{cloud_name}/video/upload/so_0/{public_id}.jpg"
        )

    return {
        "secure_url": secure_url,
        "public_id": public_id,
        "thumbnail_url": thumbnail_url,
    }


def create_direct_upload_signature(*, folder: str = EDUCATION_VIDEO_FOLDER) -> dict:
    """Return short-lived parameters for a signed direct Cloudinary upload."""
    if not cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured.")

    timestamp = int(time.time())
    params = {"folder": folder, "timestamp": timestamp}
    api_secret = current_app.config["CLOUDINARY_API_SECRET"]
    return {
        "cloud_name": current_app.config["CLOUDINARY_CLOUD_NAME"],
        "api_key": current_app.config["CLOUDINARY_API_KEY"],
        "timestamp": timestamp,
        "folder": folder,
        "signature": cloudinary.utils.api_sign_request(params, api_secret),
    }


def validate_direct_upload_result(payload: dict, *, folder: str = EDUCATION_VIDEO_FOLDER) -> dict:
    """Validate a signed Cloudinary response before persisting its asset details."""
    if not cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured.")

    public_id = str(payload.get("public_id") or "")
    secure_url = str(payload.get("secure_url") or "")
    response_signature = str(payload.get("signature") or "")
    try:
        version = int(payload.get("version"))
        byte_count = int(payload.get("bytes"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Cloudinary upload response is missing size or version.") from exc

    if not public_id.startswith(f"{folder}/"):
        raise ValueError("Cloudinary upload is outside the education video folder.")
    if byte_count < 1 or byte_count > MAX_VIDEO_BYTES:
        raise ValueError("Video must be 200 MB or smaller.")
    if payload.get("resource_type") != "video":
        raise ValueError("Cloudinary response is not a video asset.")

    parsed_url = urlparse(secure_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "res.cloudinary.com":
        raise ValueError("Cloudinary returned an invalid secure video URL.")
    if not response_signature or not cloudinary.utils.verify_api_response_signature(
        public_id,
        version,
        response_signature,
    ):
        raise ValueError("Cloudinary upload response signature is invalid.")

    cloud_name = current_app.config["CLOUDINARY_CLOUD_NAME"]
    thumbnail_url = (
        f"https://res.cloudinary.com/{cloud_name}/video/upload/so_0/{public_id}.jpg"
    )
    return {
        "secure_url": secure_url,
        "public_id": public_id,
        "thumbnail_url": thumbnail_url,
    }


def classify_cloudinary_upload_error(exc: Exception) -> tuple[str, str, int]:
    """Map provider exceptions to safe API errors while logs retain the traceback."""
    if isinstance(exc, cloudinary.exceptions.AuthorizationRequired):
        return (
            "education.cloudinary_auth_failed",
            "Video hosting credentials were rejected. Check the Railway Cloudinary settings.",
            502,
        )
    if isinstance(exc, cloudinary.exceptions.RateLimited):
        return (
            "education.cloudinary_rate_limited",
            "Video hosting is rate-limited. Please wait and try again.",
            503,
        )
    if isinstance(exc, (cloudinary.exceptions.BadRequest, cloudinary.exceptions.NotAllowed)):
        detail = str(exc).lower()
        if any(marker in detail for marker in ("too large", "file size", "maximum", "413")):
            return (
                "validation.video_too_large",
                "The video exceeds the upload limit. The maximum is 200 MB.",
                413,
            )
        return (
            "education.video_rejected",
            "The video host rejected this file. Check its format and the account upload limit.",
            422,
        )
    if isinstance(exc, cloudinary.exceptions.GeneralError):
        return (
            "education.cloudinary_unavailable",
            "Video hosting could not be reached. Please try again.",
            503,
        )
    if isinstance(exc, cloudinary.exceptions.Error):
        return (
            "education.video_provider_error",
            "The video host could not complete the upload.",
            502,
        )
    return (
        "education.video_upload_failed",
        "An unexpected server error interrupted the video upload.",
        500,
    )


def destroy_education_video(public_id: str) -> None:
    if not public_id:
        return
    if not cloudinary_configured():
        logger.warning("Skipping Cloudinary destroy; credentials not configured.")
        return
    cloudinary.uploader.destroy(public_id, resource_type="video")
