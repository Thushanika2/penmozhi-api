from app.extensions import db
from app.utils import utc_now


class ForumComment(db.Model):
    """Supports POST /api/forum/:id/comments from the route specification."""

    __tablename__ = "forum_comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id"), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    posted_at = db.Column(db.DateTime, default=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

    forum_post = db.relationship("ForumPost", back_populates="comments")
    user_profile = db.relationship("UserProfile", back_populates="forum_comments")

    def to_dict(self, anonymous=True):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "profile_id": None if anonymous else self.profile_id,
            "body": self.body,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "author_display": "Anonymous",
        }
