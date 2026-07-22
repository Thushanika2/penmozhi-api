from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.educational_resource_model import EducationalResource
from app.models.forum_comment_model import ForumComment
from app.models.forum_post_model import ForumPost
from app.utils import utc_now


def _post_to_public_dict(post, include_comments=False):
    payload = post.to_dict(anonymous=True)
    payload["author_display"] = "Anonymous"
    if include_comments:
        payload["comments"] = [c.to_dict(anonymous=True) for c in post.comments]
    return payload


def _validate_post_payload(data, post_id=None):
    errors = []
    if not data:
        return ["Request body is required."]

    if post_id is None:
        if data.get("title") is None or str(data.get("title")).strip() == "":
            errors.append("title is required.")
        if data.get("body") is None or str(data.get("body")).strip() == "":
            errors.append("body is required.")

    if data.get("content_id") is not None and str(data.get("content_id")).strip() != "":
        try:
            content_id = int(data.get("content_id"))
            if not db.session.get(EducationalResource, content_id):
                errors.append("content_id references an educational resource that does not exist.")
        except (TypeError, ValueError):
            errors.append("content_id must be an integer.")

    return errors


def get_forum_posts():
    posts = ForumPost.query.order_by(ForumPost.posted_at.desc()).all()
    return jsonify({"forum_posts": [_post_to_public_dict(p) for p in posts]}), 200


def get_forum_post(post_id):
    post = db.session.get(ForumPost, post_id)
    if not post:
        return error_response("forum.post_not_found", "Forum post not found.", 404)
    return jsonify({"forum_post": _post_to_public_dict(post, include_comments=True)}), 200


def create_forum_post():
    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_post_payload(data)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        content_id = data.get("content_id")
        if content_id is None or str(content_id).strip() == "":
            content_id = None
        else:
            content_id = int(content_id)

        post = ForumPost(
            profile_id=current_user.id,
            content_id=content_id,
            title=str(data.get("title")).strip(),
            body=str(data.get("body")).strip(),
            posted_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        return message_response(
            "forum.post_created",
            "Forum post created successfully.",
            201,
            forum_post=_post_to_public_dict(post),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def update_forum_post(post_id):
    post = db.session.get(ForumPost, post_id)
    if not post:
        return error_response("forum.post_not_found", "Forum post not found.", 404)
    if post.profile_id != current_user.id:
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    errors = _validate_post_payload(data, post_id=post_id)
    if errors:
        return validation_errors([("validation.invalid_payload", msg) for msg in errors], 400)

    try:
        if "title" in data and data.get("title") is not None:
            post.title = str(data.get("title")).strip()
        if "body" in data and data.get("body") is not None:
            post.body = str(data.get("body")).strip()
        if "content_id" in data:
            value = data.get("content_id")
            post.content_id = int(value) if value is not None and str(value).strip() != "" else None

        db.session.commit()
        return message_response(
            "forum.post_updated",
            "Forum post updated successfully.",
            200,
            forum_post=_post_to_public_dict(post),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def delete_forum_post(post_id):
    post = db.session.get(ForumPost, post_id)
    if not post:
        return error_response("forum.post_not_found", "Forum post not found.", 404)

    is_owner = post.profile_id == current_user.id
    is_admin = current_user.role == "admin"
    if not is_owner and not is_admin:
        return error_response("auth.forbidden", "Access forbidden: insufficient permissions.", 403)

    try:
        db.session.delete(post)
        db.session.commit()
        return message_response("forum.post_deleted", "Forum post deleted successfully.", 200)
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def create_forum_comment(post_id):
    post = db.session.get(ForumPost, post_id)
    if not post:
        return error_response("forum.post_not_found", "Forum post not found.", 404)

    data = request.get_json(silent=True)
    if not data:
        return error_response("request.body_required", "Request body is required.", 400)

    body = data.get("body")
    if body is None or str(body).strip() == "":
        return validation_errors([("validation.body_required", "body is required.")], 400)

    try:
        comment = ForumComment(
            post_id=post.id,
            profile_id=current_user.id,
            body=str(body).strip(),
            posted_at=utc_now(),
        )
        db.session.add(comment)
        db.session.commit()
        return message_response(
            "forum.comment_created",
            "Comment created successfully.",
            201,
            forum_comment=comment.to_dict(anonymous=True),
        )
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)
