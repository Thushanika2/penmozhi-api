from app.extensions import db
from app.utils import utc_now


class CycleHistoryLog(db.Model):
    __tablename__ = "cycle_history_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    cycle_start_date = db.Column(db.Date, nullable=False)
    cycle_end_date = db.Column(db.Date, nullable=False)
    flow_intensity = db.Column(db.String(50), nullable=False)
    predicted_next_period_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="cycle_history_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "cycle_start_date": (
                self.cycle_start_date.isoformat() if self.cycle_start_date else None
            ),
            "cycle_end_date": (
                self.cycle_end_date.isoformat() if self.cycle_end_date else None
            ),
            "flow_intensity": self.flow_intensity,
            "predicted_next_period_date": (
                self.predicted_next_period_date.isoformat()
                if self.predicted_next_period_date
                else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
