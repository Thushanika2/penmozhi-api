from app.extensions import db
from app.utils import utc_now


class ForumPost(db.Model):
    __tablename__ = "forum_posts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    content_id = db.Column(
        db.Integer,
        db.ForeignKey("educational_resources.id"),
        nullable=True,
    )
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    posted_at = db.Column(db.DateTime, default=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="forum_posts")
    educational_resource = db.relationship(
        "EducationalResource",
        back_populates="forum_posts",
    )
    comments = db.relationship(
        "ForumComment",
        back_populates="forum_post",
        cascade="all, delete-orphan",
    )

    def to_dict(self, anonymous=False):
        return {
            "id": self.id,
            "profile_id": None if anonymous else self.profile_id,
            "content_id": self.content_id,
            "title": self.title,
            "body": self.body,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "author_display": "Anonymous" if anonymous else None,
        }
