from app.extensions import db
from app.utils import utc_now


class SymptomTrackingLog(db.Model):
    __tablename__ = "symptom_tracking_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=utc_now)
    category = db.Column(db.String(100), nullable=False)
    pain_severity = db.Column(db.Integer, nullable=False)
    mood_status = db.Column(db.String(100), nullable=True)
    sleep_metrics = db.Column(db.String(255), nullable=True)
    disorder_status_id = db.Column(
        db.Integer,
        db.ForeignKey("pcos_disorder_statuses.id"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="symptom_tracking_logs")
    disorder_status = db.relationship(
        "PCOSDisorderStatus",
        back_populates="symptom_tracking_logs",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "date_time": self.date_time.isoformat() if self.date_time else None,
            "category": self.category,
            "pain_severity": self.pain_severity,
            "mood_status": self.mood_status,
            "sleep_metrics": self.sleep_metrics,
            "disorder_status_id": self.disorder_status_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
