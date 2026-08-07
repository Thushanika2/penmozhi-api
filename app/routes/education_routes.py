from flask import Blueprint

from app.controllers import education_controller as ctrl
from app.controllers import education_video_controller as video_ctrl
from app.middleware import roles_required

education_bp = Blueprint("education", __name__, url_prefix="/api/education")


@education_bp.route("", methods=["GET"])
def get_education_resources():
    return ctrl.get_education_resources()


# Standalone videos — register before /<int:resource_id> so "videos" is not captured.
@education_bp.route("/videos", methods=["GET"])
def list_education_videos():
    return video_ctrl.list_public_education_videos()


@education_bp.route("/videos/<int:video_id>", methods=["GET"])
def get_education_video(video_id):
    return video_ctrl.get_public_education_video(video_id)


@education_bp.route("/<int:resource_id>", methods=["GET"])
def get_education_resource(resource_id):
    return ctrl.get_education_resource(resource_id)


@education_bp.route("", methods=["POST"])
@roles_required("admin")
def create_education_resource():
    return ctrl.create_education_resource()


@education_bp.route("/<int:resource_id>", methods=["PUT"])
@roles_required("admin")
def update_education_resource(resource_id):
    return ctrl.update_education_resource(resource_id)


@education_bp.route("/<int:resource_id>", methods=["DELETE"])
@roles_required("admin")
def delete_education_resource(resource_id):
    return ctrl.delete_education_resource(resource_id)
