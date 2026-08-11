from app.extensions import db
from app.utils import utc_now


class SharingInvite(db.Model):
    __tablename__ = "sharing_invites"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invited_email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    sharer_user_id = db.Column(
        db.Integer, db.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    verification_attempts = db.Column(db.Integer, nullable=False, default=0)
    used_by_user_id = db.Column(
        db.Integer, db.ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True
    )

    sharer = db.relationship("UserProfile", foreign_keys=[sharer_user_id])
    used_by = db.relationship("UserProfile", foreign_keys=[used_by_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "invited_email": self.invited_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "status": self.status,
        }


class SharedConnection(db.Model):
    __tablename__ = "shared_connections"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sharer_user_id = db.Column(
        db.Integer, db.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    viewer_user_id = db.Column(
        db.Integer, db.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable unique keys enforce one active role portably. They are cleared on
    # disconnect, allowing a new row while preserving the historical record.
    active_sharer_user_id = db.Column(db.Integer, nullable=True, unique=True)
    active_viewer_user_id = db.Column(db.Integer, nullable=True, unique=True)
    status = db.Column(db.String(20), nullable=False, default="active", index=True)
    connected_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    disconnected_at = db.Column(db.DateTime, nullable=True)

    sharer = db.relationship("UserProfile", foreign_keys=[sharer_user_id])
    viewer = db.relationship("UserProfile", foreign_keys=[viewer_user_id])

    def to_dict(self, current_user_id=None):
        return {
            "id": self.id,
            "status": self.status,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "role": "sharer" if current_user_id == self.sharer_user_id else "viewer",
            "sharer": {"name": self.sharer.full_name, "email": self.sharer.email},
            "viewer": {"name": self.viewer.full_name, "email": self.viewer.email},
        }
