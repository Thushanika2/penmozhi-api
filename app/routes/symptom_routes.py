from flask import Blueprint

from app.controllers import symptom_controller as ctrl
from app.middleware import roles_required

symptom_bp = Blueprint("symptoms", __name__, url_prefix="/api/symptoms")


@symptom_bp.route("", methods=["POST"])
@roles_required("user")
def create_symptom():
    return ctrl.create_symptom()


@symptom_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_symptoms():
    return ctrl.get_my_symptoms()


@symptom_bp.route("/trends", methods=["GET"])
@roles_required("user")
def get_symptom_trends():
    return ctrl.get_symptom_trends()
