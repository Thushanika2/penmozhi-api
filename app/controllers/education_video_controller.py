import logging

from flask import jsonify, request
from flask_jwt_extended import current_user
from sqlalchemy import inspect, text

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.education_video_model import EducationVideo
from app.services.cloudinary_service import (
    destroy_education_video,
    upload_education_video,
    validate_video_file,
)
from app.utils import utc_now

logger = logging.getLogger(__name__)

_schema_ready = False


def _ensure_education_videos_schema() -> None:
    """Create education_videos table if Alembic has not caught up yet."""
    global _schema_ready
    if _schema_ready:
        return
    try:
        inspector = inspect(db.engine)
        if "education_videos" not in inspector.get_table_names():
            db.session.execute(
                text(
                    """
                    CREATE TABLE `education_videos` (
                      `id` INT NOT NULL AUTO_INCREMENT,
                      `title` VARCHAR(255) NOT NULL,
                      `description` TEXT NULL,
                      `video_url` VARCHAR(512) NOT NULL,
                      `video_public_id` VARCHAR(255) NOT NULL,
                      `thumbnail_url` VARCHAR(512) NULL,
                      `category` VARCHAR(100) NOT NULL,
                      `created_by_admin_id` INT NOT NULL,
                      `created_at` DATETIME NULL,
                      `updated_at` DATETIME NULL,
                      PRIMARY KEY (`id`),
                      CONSTRAINT `fk_education_videos_admin`
                        FOREIGN KEY (`created_by_admin_id`)
                        REFERENCES `user_profiles` (`id`)
                    )
                    """
                )
            )
            db.session.commit()
            logger.info("Created education_videos table")
        _schema_ready = True
    except Exception:
        db.session.rollback()
        logger.exception("Failed to ensure education_videos schema")


def list_public_education_videos():
    _ensure_education_videos_schema()
    query = EducationVideo.query
    category = request.args.get("category")
    if category:
        query = query.filter(EducationVideo.category.ilike(str(category).strip()))
    videos = query.order_by(EducationVideo.created_at.desc()).all()
    return jsonify({"education_videos": [v.to_list_dict() for v in videos]}), 200


def get_public_education_video(video_id):
    _ensure_education_videos_schema()
    video = db.session.get(EducationVideo, video_id)
    if not video:
        return error_response("education.video_entry_not_found", "Education video not found.", 404)
    return jsonify({"education_video": video.to_dict(include_video_url=True)}), 200


def list_admin_education_videos():
    _ensure_education_videos_schema()
    query = EducationVideo.query
    category = request.args.get("category")
    if category:
        query = query.filter(EducationVideo.category.ilike(str(category).strip()))
    videos = query.order_by(EducationVideo.created_at.desc()).all()
    return jsonify({
        "education_videos": [v.to_dict(include_video_url=True, admin=True) for v in videos],
    }), 200


def create_admin_education_video():
    _ensure_education_videos_schema()

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    category = (request.form.get("category") or "").strip()
    file_storage = request.files.get("video") or request.files.get("file")

    errors = []
    if not title:
        errors.append(("validation.title_required", "title is required."))
    if not category:
        errors.append(("validation.category_required", "category is required."))
    validation_error = validate_video_file(file_storage)
    if validation_error:
        errors.append(("validation.video_invalid", validation_error))

    content_length = request.content_length
    if content_length and content_length > 200 * 1024 * 1024:
        errors.append(("validation.video_too_large", "Video must be 200 MB or smaller."))

    if errors:
        return validation_errors(errors, 400)

    try:
        uploaded = upload_education_video(file_storage, folder="penmozhi/education/videos")
        secure_url = uploaded.get("secure_url")
        public_id = uploaded.get("public_id")
        if not secure_url or not public_id:
            return error_response(
                "education.video_upload_failed",
                "Cloudinary did not return a video URL.",
                502,
            )

        now = utc_now()
        video = EducationVideo(
            title=title,
            description=description,
            video_url=secure_url,
            video_public_id=public_id,
            thumbnail_url=uploaded.get("thumbnail_url"),
            category=category,
            created_by_admin_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(video)
        db.session.commit()
        return message_response(
            "education.video_entry_created",
            "Education video created successfully.",
            201,
            education_video=video.to_dict(include_video_url=True, admin=True),
        )
    except RuntimeError as exc:
        db.session.rollback()
        return error_response("education.cloudinary_not_configured", str(exc), 503)
    except Exception:
        db.session.rollback()
        logger.exception("Failed to create education video")
        return error_response(
            "education.video_upload_failed",
            "Video upload failed. Please try again.",
            500,
        )


def update_admin_education_video(video_id):
    _ensure_education_videos_schema()
    video = db.session.get(EducationVideo, video_id)
    if not video:
        return error_response("education.video_entry_not_found", "Education video not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = []
    if "title" in data:
        title = str(data.get("title") or "").strip()
        if not title:
            errors.append(("validation.title_required", "title is required."))
        else:
            video.title = title
    if "category" in data:
        category = str(data.get("category") or "").strip()
        if not category:
            errors.append(("validation.category_required", "category is required."))
        else:
            video.category = category
    if "description" in data:
        description = data.get("description")
        video.description = str(description).strip() if description is not None else None

    if errors:
        return validation_errors(errors, 400)

    try:
        video.updated_at = utc_now()
        db.session.commit()
        return message_response(
            "education.video_entry_updated",
            "Education video updated successfully.",
            200,
            education_video=video.to_dict(include_video_url=True, admin=True),
        )
    except Exception:
        db.session.rollback()
        logger.exception("Failed to update education video id=%s", video_id)
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_admin_education_video(video_id):
    _ensure_education_videos_schema()
    video = db.session.get(EducationVideo, video_id)
    if not video:
        return error_response("education.video_entry_not_found", "Education video not found.", 404)

    public_id = video.video_public_id
    try:
        db.session.delete(video)
        db.session.commit()
        if public_id:
            try:
                destroy_education_video(public_id)
            except Exception:
                logger.exception(
                    "Failed to destroy Cloudinary video after education video delete public_id=%s",
                    public_id,
                )
        return message_response(
            "education.video_entry_deleted",
            "Education video deleted successfully.",
            200,
        )
    except Exception:
        db.session.rollback()
        logger.exception("Failed to delete education video id=%s", video_id)
        return error_response("server.internal_error", "An internal server error occurred.", 500)
