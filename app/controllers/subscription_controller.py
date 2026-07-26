from flask import jsonify, request
from flask_jwt_extended import current_user

from app.api_responses import error_response, message_response
from app.extensions import db
from app.models.subscription_model import Subscription
from app.utils import utc_now


def get_my_subscription():
    sub = Subscription.query.filter_by(profile_id=current_user.id).first()
    if not sub:
        return jsonify({
            "subscription": {
                "plan": "free",
                "status": "active",
                "current_period_end": None,
            },
        }), 200
    return jsonify({"subscription": sub.to_dict()}), 200


def checkout():
    data = request.get_json(silent=True) or {}
    plan = str(data.get("plan", "plus")).strip().lower()

    # TODO: Integrate real payment provider (Stripe/Razorpay) for checkout session.
    try:
        sub = Subscription.query.filter_by(profile_id=current_user.id).first()
        if not sub:
            sub = Subscription(profile_id=current_user.id)
            db.session.add(sub)

        sub.plan = plan if plan in ("free", "plus") else "plus"
        sub.status = "pending_payment"
        db.session.commit()

        return jsonify({
            "message": "Checkout stub — payment integration pending.",
            "message_code": "subscriptions.checkout_stub",
            "checkout_url": None,
            "subscription": sub.to_dict(),
            "todo": "Implement real payment checkout session and redirect URL.",
        }), 200
    except Exception:
        db.session.rollback()
        return error_response("server.internal_error", "An internal server error occurred.", 500)


def webhook():
    # TODO: Verify webhook signature from payment provider and update subscription status.
    payload = request.get_json(silent=True) or {}
    return jsonify({
        "message": "Webhook received (stub).",
        "message_code": "subscriptions.webhook_stub",
        "received": payload,
        "todo": "Implement payment webhook verification and subscription lifecycle updates.",
    }), 200
