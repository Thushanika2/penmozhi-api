from app.extensions import db
from app.utils import utc_now


class PregnancyProfile(db.Model):
    __tablename__ = "pregnancy_profiles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=False,
        unique=True,
    )
    last_menstrual_period = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    current_trimester = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="pregnancy_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "last_menstrual_period": (
                self.last_menstrual_period.isoformat() if self.last_menstrual_period else None
            ),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "current_trimester": self.current_trimester,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
