from app.extensions import db
from app.utils import utc_now


class AIHealthAssistantSession(db.Model):
    __tablename__ = "ai_health_assistant_sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("user_profiles.id"), nullable=False)
    symptom_analysis_log = db.Column(db.Text, nullable=True)
    generated_recommendations = db.Column(db.Text, nullable=True)
    posted_messages = db.Column(db.Text, nullable=True)
    saved_chat_sessions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="ai_sessions")

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "symptom_analysis_log": self.symptom_analysis_log,
            "generated_recommendations": self.generated_recommendations,
            "posted_messages": self.posted_messages,
            "saved_chat_sessions": self.saved_chat_sessions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
