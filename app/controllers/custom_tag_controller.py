from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.custom_tag_model import CustomTag


def _get_owned_custom_tag(tag_id):
    tag = db.session.get(CustomTag, tag_id)
    if not tag:
        return None, error_response("custom_tags.not_found", "Custom tag not found.", 404)
    if tag.profile_id != current_user.id:
        return None, error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)
    return tag, None


def _validate_custom_tag_payload(data, tag_id=None):
    errors = []
    if not data:
        return ["Request body is required."]

    if tag_id is None or "label" in data:
        if data.get("label") is None or str(data.get("label")).strip() == "":
            errors.append("label is required.")

    return errors


def create_custom_tag():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_custom_tag_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    label = str(data.get("label")).strip()
    existing = CustomTag.query.filter_by(profile_id=current_user.id, label=label).first()
    if existing:
        return validation_errors([("validation.label_exists", "A tag with this label already exists.")], 400)

    try:
        tag = CustomTag(
            profile_id=current_user.id,
            label=label,
            icon=str(data.get("icon")).strip() if data.get("icon") else None,
        )
        db.session.add(tag)
        db.session.commit()
        return message_response(
            "custom_tags.created_success",
            "Custom tag created successfully.",
            201,
            custom_tag=tag.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def get_my_custom_tags():
    tags = (
        CustomTag.query.filter_by(profile_id=current_user.id)
        .order_by(CustomTag.label.asc())
        .all()
    )
    return jsonify({"custom_tags": [t.to_dict() for t in tags]}), 200


def update_custom_tag(tag_id):
    tag, error = _get_owned_custom_tag(tag_id)
    if error:
        return error

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_custom_tag_payload(data, tag_id=tag_id)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "label" in data and data.get("label") is not None:
            label = str(data.get("label")).strip()
            duplicate = CustomTag.query.filter(
                CustomTag.profile_id == current_user.id,
                CustomTag.label == label,
                CustomTag.id != tag.id,
            ).first()
            if duplicate:
                return validation_errors(
                    [("validation.label_exists", "A tag with this label already exists.")],
                    400,
                )
            tag.label = label
        if "icon" in data:
            tag.icon = str(data.get("icon")).strip() if data.get("icon") else None

        db.session.commit()
        return message_response(
            "custom_tags.updated_success",
            "Custom tag updated successfully.",
            200,
            custom_tag=tag.to_dict(),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_custom_tag(tag_id):
    tag, error = _get_owned_custom_tag(tag_id)
    if error:
        return error

    try:
        db.session.delete(tag)
        db.session.commit()
        return message_response("custom_tags.deleted_success", "Custom tag deleted successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
