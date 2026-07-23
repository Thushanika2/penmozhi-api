from flask import jsonify, request
from flask_jwt_extended import current_user

from app.services.insights_service import compute_health_insights


def get_insights():
    months = request.args.get("months", default=6, type=int)
    payload = compute_health_insights(current_user, months=months)
    return jsonify(payload), 200
