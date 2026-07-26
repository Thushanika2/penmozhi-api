from app.extensions import db
from app.utils import utc_now


class PerimenopauseLog(db.Model):
    __tablename__ = "perimenopause_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    hot_flashes = db.Column(db.Boolean, nullable=False, default=False)
    night_sweats = db.Column(db.Boolean, nullable=False, default=False)
    mood_changes = db.Column(db.String(255), nullable=True)
    sleep_disruption = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="perimenopause_logs")

    __table_args__ = (
        db.UniqueConstraint("profile_id", "log_date", name="uq_perimenopause_log_profile_date"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "log_date": self.log_date.isoformat() if self.log_date else None,
            "hot_flashes": self.hot_flashes,
            "night_sweats": self.night_sweats,
            "mood_changes": self.mood_changes,
            "sleep_disruption": self.sleep_disruption,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
