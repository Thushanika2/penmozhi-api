from app.extensions import db
from app.utils import utc_now


class MedicationSupplementReminder(db.Model):
    __tablename__ = "medication_supplement_reminders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    reminder_type = db.Column(db.String(50), nullable=False)
    scheduled_time = db.Column(db.Time, nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    adherence_status = db.Column(db.String(50), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="medication_reminders")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "item_name": self.item_name,
            "reminder_type": self.reminder_type,
            "scheduled_time": (
                self.scheduled_time.isoformat() if self.scheduled_time else None
            ),
            "dosage": self.dosage,
            "adherence_status": self.adherence_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
