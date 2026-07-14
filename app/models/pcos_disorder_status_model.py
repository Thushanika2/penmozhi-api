from app.extensions import db
from app.utils import utc_now


class PCOSDisorderStatus(db.Model):
    __tablename__ = "pcos_disorder_statuses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    health_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("health_profiles.id"),
        nullable=False,
    )
    disorder_type = db.Column(db.String(100), nullable=False, default="none")
    diagnosis_status = db.Column(db.String(100), nullable=False, default="not_diagnosed")
    diagnosed_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    health_profile = db.relationship(
        "HealthProfile",
        back_populates="pcos_disorder_statuses",
    )
    symptom_tracking_logs = db.relationship(
        "SymptomTrackingLog",
        back_populates="disorder_status",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "health_profile_id": self.health_profile_id,
            "disorder_type": self.disorder_type,
            "diagnosis_status": self.diagnosis_status,
            "diagnosed_date": (
                self.diagnosed_date.isoformat() if self.diagnosed_date else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
