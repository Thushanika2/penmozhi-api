from app.extensions import db
from app.utils import utc_now


class EducationVideo(db.Model):
    __tablename__ = "education_videos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(512), nullable=False)
    video_public_id = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(512), nullable=True)
    category = db.Column(db.String(100), nullable=False)
    created_by_admin_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    created_by_admin = db.relationship("UserProfile", foreign_keys=[created_by_admin_id])

    def to_list_dict(self):
        """Public list payload — no video_url."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict(self, *, include_video_url: bool = True, admin: bool = False):
        payload = self.to_list_dict()
        if include_video_url:
            payload["video_url"] = self.video_url
        if admin:
            payload["video_public_id"] = self.video_public_id
            payload["created_by_admin_id"] = self.created_by_admin_id
        return payload
