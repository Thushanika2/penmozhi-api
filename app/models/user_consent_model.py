from app.extensions import db
from app.utils import utc_now


class UserConsent(db.Model):
    __tablename__ = "user_consents"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type = db.Column(db.String(50), nullable=False)
    policy_version = db.Column(db.String(20), nullable=False)
    granted_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    context = db.Column(db.String(255), nullable=True)

    user = db.relationship("UserProfile", back_populates="user_consents")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "consent_type": self.consent_type,
            "policy_version": self.policy_version,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "context": self.context,
        }
