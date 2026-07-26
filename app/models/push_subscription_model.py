from app.extensions import db
from app.utils import utc_now


class PushSubscription(db.Model):
    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    endpoint = db.Column(db.Text, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    device_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="push_subscriptions")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "endpoint": self.endpoint,
            "p256dh": self.p256dh,
            "auth": self.auth,
            "device_type": self.device_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
