from flask import Blueprint

from app.controllers import auth_controller as ctrl
from app.middleware import jwt_required_user

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    return ctrl.register()


@auth_bp.route("/login", methods=["POST"])
def login():
    return ctrl.login()


@auth_bp.route("/logout", methods=["POST"])
@jwt_required_user
def logout():
    return ctrl.logout()


@auth_bp.route("/profile", methods=["GET"])
@jwt_required_user
def profile():
    return ctrl.profile()


@auth_bp.route("/profile", methods=["PATCH"])
@jwt_required_user
def update_profile():
    return ctrl.update_profile()


@auth_bp.route("/account", methods=["DELETE"])
@jwt_required_user
def delete_account():
    return ctrl.delete_account()


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    return ctrl.refresh()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    return ctrl.forgot_password()


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    return ctrl.reset_password()
