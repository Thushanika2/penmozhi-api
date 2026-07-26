from flask import Blueprint

from app.controllers import custom_tag_controller as ctrl
from app.middleware import roles_required

custom_tag_bp = Blueprint("custom_tags", __name__, url_prefix="/api/custom-tags")


@custom_tag_bp.route("", methods=["POST"])
@roles_required("user")
def create_custom_tag():
    return ctrl.create_custom_tag()


@custom_tag_bp.route("/my", methods=["GET"])
@roles_required("user")
def get_my_custom_tags():
    return ctrl.get_my_custom_tags()


@custom_tag_bp.route("/<int:tag_id>", methods=["PUT"])
@roles_required("user")
def update_custom_tag(tag_id):
    return ctrl.update_custom_tag(tag_id)


@custom_tag_bp.route("/<int:tag_id>", methods=["DELETE"])
@roles_required("user")
def delete_custom_tag(tag_id):
    return ctrl.delete_custom_tag(tag_id)
