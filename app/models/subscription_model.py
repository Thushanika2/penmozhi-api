from app.extensions import db
from app.utils import utc_now


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=False,
        unique=True,
    )
    plan = db.Column(db.String(20), nullable=False, default="free")
    status = db.Column(db.String(50), nullable=False, default="active")
    current_period_end = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="subscription")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "plan": self.plan,
            "status": self.status,
            "current_period_end": (
                self.current_period_end.isoformat() if self.current_period_end else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
