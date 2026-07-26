from app.extensions import db
from app.utils import utc_now


class CycleShare(db.Model):
    __tablename__ = "cycle_shares"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    shared_with_email = db.Column(db.String(120), nullable=False)
    shared_with_profile_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=True,
    )
    status = db.Column(db.String(20), nullable=False, default="pending")
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=utc_now)

    owner = db.relationship(
        "UserProfile",
        foreign_keys=[owner_profile_id],
        back_populates="cycle_shares_owned",
    )
    recipient = db.relationship(
        "UserProfile",
        foreign_keys=[shared_with_profile_id],
        back_populates="cycle_shares_received",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "owner_profile_id": self.owner_profile_id,
            "shared_with_email": self.shared_with_email,
            "shared_with_profile_id": self.shared_with_profile_id,
            "status": self.status,
            "permissions": self.permissions or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
