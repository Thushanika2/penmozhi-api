from app.extensions import db
from app.utils import utc_now


class CustomTag(db.Model):
    __tablename__ = "custom_tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    icon = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="custom_tags")
    symptom_tracking_logs = db.relationship(
        "SymptomTrackingLog",
        back_populates="custom_tag",
    )

    __table_args__ = (
        db.UniqueConstraint("profile_id", "label", name="uq_custom_tag_profile_label"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "label": self.label,
            "icon": self.icon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
