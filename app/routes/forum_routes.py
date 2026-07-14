from flask import Blueprint

from app.controllers import forum_controller as ctrl
from app.middleware import jwt_required_user, roles_required

forum_bp = Blueprint("forum", __name__, url_prefix="/api/forum")


@forum_bp.route("", methods=["GET"])
@jwt_required_user
def get_forum_posts():
    return ctrl.get_forum_posts()


@forum_bp.route("/<int:post_id>", methods=["GET"])
@jwt_required_user
def get_forum_post(post_id):
    return ctrl.get_forum_post(post_id)


@forum_bp.route("", methods=["POST"])
@roles_required("user")
def create_forum_post():
    return ctrl.create_forum_post()


@forum_bp.route("/<int:post_id>", methods=["PUT"])
@roles_required("user")
def update_forum_post(post_id):
    return ctrl.update_forum_post(post_id)


@forum_bp.route("/<int:post_id>", methods=["DELETE"])
@jwt_required_user
def delete_forum_post(post_id):
    return ctrl.delete_forum_post(post_id)


@forum_bp.route("/<int:post_id>/comments", methods=["POST"])
@roles_required("user")
def create_forum_comment(post_id):
    return ctrl.create_forum_comment(post_id)
