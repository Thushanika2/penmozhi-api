from flask import jsonify, request

from app.extensions import db
from app.models.educational_resource_model import EducationalResource
from app.utils import parse_date, utc_now


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

    return errors


def get_education_resources():
    query = EducationalResource.query
    category = request.args.get("category")
    if category:
        query = query.filter(
            EducationalResource.content_category.ilike(str(category).strip())
        )
    resources = query.order_by(EducationalResource.publication_date.desc()).all()
    return jsonify({"education_resources": [r.to_dict() for r in resources]}), 200


def get_education_resource(resource_id):
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return jsonify({"error": "Educational resource not found."}), 404
    return jsonify({"education_resource": resource.to_dict()}), 200


def create_education_resource():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    errors = _validate_education_payload(data)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        resource = EducationalResource(
            article_title=str(data.get("article_title")).strip(),
            content_category=str(data.get("content_category")).strip(),
            content_body=str(data.get("content_body")).strip(),
            publication_date=parse_date(data.get("publication_date")) or utc_now().date(),
        )
        db.session.add(resource)
        db.session.commit()
        return jsonify({
            "message": "Educational resource created successfully.",
            "education_resource": resource.to_dict(),
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred."}), 500


def update_education_resource(resource_id):
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return jsonify({"error": "Educational resource not found."}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body is required."}), 400

    errors = _validate_education_payload(data, resource_id=resource_id)
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        if "article_title" in data and data.get("article_title") is not None:
            resource.article_title = str(data.get("article_title")).strip()
        if "content_category" in data and data.get("content_category") is not None:
            resource.content_category = str(data.get("content_category")).strip()
        if "content_body" in data and data.get("content_body") is not None:
            resource.content_body = str(data.get("content_body")).strip()
        if "publication_date" in data and data.get("publication_date") is not None:
            resource.publication_date = parse_date(data.get("publication_date"))

        db.session.commit()
        return jsonify({
            "message": "Educational resource updated successfully.",
            "education_resource": resource.to_dict(),
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred."}), 500


def delete_education_resource(resource_id):
    resource = db.session.get(EducationalResource, resource_id)
    if not resource:
        return jsonify({"error": "Educational resource not found."}), 404

    try:
        db.session.delete(resource)
        db.session.commit()
        return jsonify({"message": "Educational resource deleted successfully."}), 200
    except Exception:
        db.session.rollback()
        return jsonify({"error": "An internal server error occurred."}), 500
