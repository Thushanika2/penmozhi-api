from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response, validation_errors
from app.extensions import db
from app.models.tracking_category_model import TrackingCategory


def get_tracking_categories():
    group = request.args.get("group")
    query = TrackingCategory.query
    if group:
        query = query.filter_by(group=str(group).strip())
    categories = query.order_by(TrackingCategory.group.asc(), TrackingCategory.label.asc()).all()
    return jsonify({"tracking_categories": [c.to_dict() for c in categories]}), 200
