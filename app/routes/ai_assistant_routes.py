from flask import Blueprint

from app.controllers import ai_assistant_controller as ctrl
from app.middleware import roles_required

ai_assistant_bp = Blueprint("ai_assistant", __name__, url_prefix="/api/ai-assistant")


@ai_assistant_bp.route("/chat", methods=["POST"])
@roles_required("user")
def chat():
    return ctrl.chat()


@ai_assistant_bp.route("/recommendations", methods=["GET"])
@roles_required("user")
def get_recommendations():
    return ctrl.get_recommendations()


@ai_assistant_bp.route("/history", methods=["GET"])
@roles_required("user")
def get_chat_history():
    return ctrl.get_chat_history()


@ai_assistant_bp.route("/sessions", methods=["GET"])
@roles_required("user")
def get_sessions():
    return ctrl.get_sessions()


@ai_assistant_bp.route("/chats", methods=["GET"])
@roles_required("user")
def get_chats():
    return ctrl.get_chats()
