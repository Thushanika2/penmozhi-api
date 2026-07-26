from flask import Blueprint

from app.controllers import account_controller as account_ctrl
from app.controllers import auth_controller as auth_ctrl
from app.middleware import jwt_required_user

account_bp = Blueprint("account", __name__, url_prefix="/api/account")


@account_bp.route("/export", methods=["GET"])
@jwt_required_user
def export_account_data():
    return account_ctrl.export_account_data()


@account_bp.route("", methods=["DELETE"])
@jwt_required_user
def delete_account():
    return auth_ctrl.delete_account()
