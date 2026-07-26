from app.extensions import db
from app.utils import utc_now


class WearableConnection(db.Model):
    __tablename__ = "wearable_connections"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    access_token = db.Column(db.Text, nullable=True)
    refresh_token = db.Column(db.Text, nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="wearable_connections")

    __table_args__ = (
        db.UniqueConstraint("profile_id", "provider", name="uq_wearable_profile_provider"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "provider": self.provider,
            "last_synced_at": (
                self.last_synced_at.isoformat() if self.last_synced_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
