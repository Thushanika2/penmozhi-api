from app.extensions import db
from app.utils import utc_now


class PrivacyRequest(db.Model):
    __tablename__ = "privacy_requests"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email = db.Column(db.String(120), nullable=False)
    request_type = db.Column(db.String(20), nullable=False)  # export | delete
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | processing | completed
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime, nullable=True)
    completed_by_admin_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    user = db.relationship(
        "UserProfile",
        foreign_keys=[user_id],
        back_populates="privacy_requests",
    )
    completed_by_admin = db.relationship(
        "UserProfile",
        foreign_keys=[completed_by_admin_id],
    )

    def to_dict(self):
        admin = self.completed_by_admin
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "request_type": self.request_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_by_admin_id": self.completed_by_admin_id,
            "completed_by_admin_email": admin.email if admin else None,
        }
