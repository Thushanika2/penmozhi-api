from app.extensions import db
from app.utils import utc_now


class AdminActionLog(db.Model):
    __tablename__ = "admin_action_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=False,
    )
    action_type = db.Column(db.String(50), nullable=False)
    target_user_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=True,
    )
    timestamp = db.Column(db.DateTime, nullable=False, default=utc_now)
    notes = db.Column(db.String(500), nullable=True)

    admin = db.relationship(
        "UserProfile",
        foreign_keys=[admin_id],
        backref="admin_actions_taken",
    )
    target_user = db.relationship(
        "UserProfile",
        foreign_keys=[target_user_id],
        backref="admin_actions_received",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "admin_email": self.admin.email if self.admin else None,
            "action_type": self.action_type,
            "target_user_id": self.target_user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "notes": self.notes,
        }
