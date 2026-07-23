from app.extensions import db
from app.utils import utc_now


class DailyLog(db.Model):
    __tablename__ = "daily_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    flow_level = db.Column(db.String(20), nullable=True)
    pain_level = db.Column(db.String(20), nullable=True)
    mood = db.Column(db.String(50), nullable=True)
    energy = db.Column(db.String(20), nullable=True)
    sleep_hours = db.Column(db.Float, nullable=True)
    exercise = db.Column(db.String(50), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    basal_temp = db.Column(db.Float, nullable=True)
    cervical_fluid = db.Column(db.String(20), nullable=True)
    sexual_activity = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="daily_logs")

    __table_args__ = (
        db.UniqueConstraint("profile_id", "log_date", name="uq_daily_log_profile_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "log_date": self.log_date.isoformat() if self.log_date else None,
            "flow_level": self.flow_level,
            "pain_level": self.pain_level,
            "mood": self.mood,
            "energy": self.energy,
            "sleep_hours": self.sleep_hours,
            "exercise": self.exercise,
            "weight": self.weight,
            "basal_temp": self.basal_temp,
            "cervical_fluid": self.cervical_fluid,
            "sexual_activity": self.sexual_activity,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
