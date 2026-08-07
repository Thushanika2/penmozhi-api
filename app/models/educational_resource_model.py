from app.extensions import db
from app.utils import utc_now


class EducationalResource(db.Model):
    __tablename__ = "educational_resources"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    article_title = db.Column(db.String(255), nullable=False)
    content_category = db.Column(db.String(100), nullable=False)
    content_body = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), nullable=False, default="english", server_default="english")
    publication_date = db.Column(db.Date, nullable=False)
    video_url = db.Column(db.String(512), nullable=True)
    video_public_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    forum_posts = db.relationship("ForumPost", back_populates="educational_resource")

    def to_dict(self):
        return {
            "id": self.id,
            "article_title": self.article_title,
            "content_category": self.content_category,
            "content_body": self.content_body,
            "language": self.language or "english",
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date else None
            ),
            "video_url": self.video_url,
            "video_public_id": self.video_public_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
