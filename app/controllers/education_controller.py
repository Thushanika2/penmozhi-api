import logging

from flask import jsonify, request
from sqlalchemy import inspect, text

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.educational_resource_model import EducationalResource
from app.services.cloudinary_service import (
    EDUCATION_VIDEO_FOLDER,
    MAX_VIDEO_BYTES,
    classify_cloudinary_upload_error,
    destroy_education_video,
    upload_education_video,
    validate_direct_upload_result,
    validate_video_file,
)
from app.utils import parse_date, utc_now

logger = logging.getLogger(__name__)

_video_schema_ready = False


def _ensure_education_video_schema() -> None:
    """Idempotently add video columns when Alembic has not caught up yet."""
    global _video_schema_ready
    if _video_schema_ready:
        return
    try:
        inspector = inspect(db.engine)
        if "educational_resources" not in inspector.get_table_names():
            _video_schema_ready = True
            return
        columns = {col["name"] for col in inspector.get_columns("educational_resources")}
        altered = False
        if "video_url" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE `educational_resources` "
                    "ADD COLUMN `video_url` VARCHAR(512) NULL"
                )
            )
            altered = True
        if "video_public_id" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE `educational_resources` "
                    "ADD COLUMN `video_public_id` VARCHAR(255) NULL"
                )
            )
            altered = True
        if altered:
            db.session.commit()
            logger.info("Added educational_resources video columns")
        _video_schema_ready = True
    except Exception:
        db.session.rollback()
        logger.exception("Failed to ensure educational_resources video schema")


def _normalize_language(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in ("english", "en"):
        return "english"
    if normalized in ("tamil", "ta"):
        return "tamil"
    return None


def _validate_education_payload(data, resource_id=None):
    errors = []
    if not data:
        return ["Request body is required."]

    required = ("article_title", "content_category", "content_body", "publication_date")
    if resource_id is None:
        for field in required:
            if data.get(field) is None or str(data.get(field)).strip() == "":
                errors.append(f"{field} is required.")

    if data.get("publication_date"):
        try:
            parse_date(data.get("publication_date"))
        except ValueError:
            errors.append("publication_date must be a valid date (YYYY-MM-DD).")

    if "language" in data and data.get("language") is not None:
        if _normalize_language(data.get("language")) is None:
            errors.append("language must be 'english' or 'tamil'.")

    return errors


def get_education_resources():
    _ensure_education_video_schema()
    query = EducationalResource.query
    category = request.args.get("category")
    if category:
        query = query.filter(
            EducationalResource.content_category.ilike(str(category).strip())
        )
    language = _normalize_language(request.args.get("language"))
    if language:
        query = query.filter(EducationalResource.language == language)
    resources = query.order_by(EducationalResource.publication_date.desc()).all()
    return jsonify({"education_resources": [r.to_dict() for r in resources]}), 200


def get_education_resource(resource_id):
    _ensure_education_video_schema()
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return error_response("education.not_found", "Educational resource not found.", 404)
    return jsonify({"education_resource": resource.to_dict()}), 200


def create_education_resource():
    _ensure_education_video_schema()
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_education_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        resource = EducationalResource(
            article_title=str(data.get("article_title")).strip(),
            content_category=str(data.get("content_category")).strip(),
            content_body=str(data.get("content_body")).strip(),
            language=_normalize_language(data.get("language")) or "english",
            publication_date=parse_date(data.get("publication_date")) or utc_now().date(),
        )
        db.session.add(resource)
        db.session.commit()
        return message_response(
            "education.created_success",
            "Educational resource created successfully.",
            201,
            education_resource=resource.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def update_education_resource(resource_id):
    _ensure_education_video_schema()
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return error_response("education.not_found", "Educational resource not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_education_payload(data, resource_id=resource_id)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "article_title" in data and data.get("article_title") is not None:
            resource.article_title = str(data.get("article_title")).strip()
        if "content_category" in data and data.get("content_category") is not None:
            resource.content_category = str(data.get("content_category")).strip()
        if "content_body" in data and data.get("content_body") is not None:
            resource.content_body = str(data.get("content_body")).strip()
        if "language" in data and data.get("language") is not None:
            resource.language = _normalize_language(data.get("language")) or resource.language
        if "publication_date" in data and data.get("publication_date") is not None:
            resource.publication_date = parse_date(data.get("publication_date"))

        db.session.commit()
        return message_response(
            "education.updated_success",
            "Educational resource updated successfully.",
            200,
            education_resource=resource.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_education_resource(resource_id):
    _ensure_education_video_schema()
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return error_response("education.not_found", "Educational resource not found.", 404)

    try:
        public_id = resource.video_public_id
        db.session.delete(resource)
        db.session.commit()
        if public_id:
            try:
                destroy_education_video(public_id)
            except Exception:
                logger.exception(
                    "Failed to destroy Cloudinary video after article delete public_id=%s",
                    public_id,
                )
        return message_response(
            "education.deleted_success",
            "Educational resource deleted successfully.",
            200,
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def upload_education_resource_video(resource_id):
    _ensure_education_video_schema()
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return error_response("education.not_found", "Educational resource not found.", 404)

    direct_payload = request.get_json(silent=True) if request.is_json else None
    file_storage = None
    if direct_payload is None:
        file_storage = request.files.get("video") or request.files.get("file")
        validation_error = validate_video_file(file_storage)
        if validation_error:
            validation_code = (
                "validation.video_too_large"
                if "200 MB" in validation_error
                else "validation.video_invalid"
            )
            return validation_errors(
                [(validation_code, validation_error)],
                413 if validation_code == "validation.video_too_large" else 400,
            )
    elif not isinstance(direct_payload, dict) or not isinstance(
        direct_payload.get("upload"), dict
    ):
        return validation_errors(
            [("validation.video_invalid", "A completed Cloudinary video upload is required.")],
            400,
        )

    content_length = request.content_length
    if direct_payload is None and content_length and content_length > MAX_VIDEO_BYTES:
        return validation_errors(
            [("validation.video_too_large", "Video must be 200 MB or smaller.")],
            413,
        )

    previous_public_id = resource.video_public_id
    uploaded = None
    try:
        if direct_payload is not None:
            uploaded = validate_direct_upload_result(
                direct_payload["upload"],
                folder=EDUCATION_VIDEO_FOLDER,
            )
        else:
            uploaded = upload_education_video(file_storage, folder=EDUCATION_VIDEO_FOLDER)
        secure_url = uploaded.get("secure_url")
        public_id = uploaded.get("public_id")
        if not secure_url or not public_id:
            return error_response(
                "education.video_invalid_response",
                "The video host returned an incomplete upload response.",
                502,
            )
    except RuntimeError as exc:
        db.session.rollback()
        logger.exception("Cloudinary is not configured for article video upload")
        return error_response("education.cloudinary_not_configured", str(exc), 503)
    except ValueError as exc:
        db.session.rollback()
        logger.exception("Rejected invalid direct Cloudinary article upload response")
        if "200 MB" in str(exc):
            return error_response("validation.video_too_large", str(exc), 413)
        return error_response(
            "education.video_invalid_response",
            "The completed video upload could not be verified. Please upload it again.",
            400,
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception("Education video upload failed for resource_id=%s", resource_id)
        code, message, status = classify_cloudinary_upload_error(exc)
        return error_response(code, message, status)

    try:
        resource.video_url = secure_url
        resource.video_public_id = public_id
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception(
            "Video reached Cloudinary but article save failed resource_id=%s public_id=%s",
            resource_id,
            public_id,
        )
        try:
            destroy_education_video(public_id)
        except Exception:
            logger.exception(
                "Failed to clean up Cloudinary asset after article save failure public_id=%s",
                public_id,
            )
        return error_response(
            "education.video_save_failed",
            "The video uploaded, but its education record could not be saved.",
            500,
        )

    if previous_public_id and previous_public_id != public_id:
        try:
            destroy_education_video(previous_public_id)
        except Exception:
            logger.exception(
                "Failed to destroy previous Cloudinary video public_id=%s",
                previous_public_id,
            )

    return message_response(
        "education.video_uploaded",
        "Video uploaded successfully.",
        200,
        education_resource=resource.to_dict(),
    )


def delete_education_resource_video(resource_id):
    _ensure_education_video_schema()
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return error_response("education.not_found", "Educational resource not found.", 404)

    if not resource.video_url and not resource.video_public_id:
        return error_response("education.video_not_found", "This article has no video.", 404)

    public_id = resource.video_public_id
    try:
        resource.video_url = None
        resource.video_public_id = None
        db.session.commit()
        if public_id:
            try:
                destroy_education_video(public_id)
            except Exception:
                logger.exception(
                    "Failed to destroy Cloudinary video public_id=%s",
                    public_id,
                )
        return message_response(
            "education.video_removed",
            "Video removed successfully.",
            200,
            education_resource=resource.to_dict(),
        )
    except Exception:
        db.session.rollback()
        logger.exception("Education video delete failed for resource_id=%s", resource_id)
        return error_response("server.internal_error", "An internal server error occurred.", 500)
