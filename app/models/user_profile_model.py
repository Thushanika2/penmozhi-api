from app.extensions import db
from app.utils import utc_now
from werkzeug.security import check_password_hash, generate_password_hash


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(255), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    language_preference = db.Column(db.String(20), nullable=False, default="english")
    country = db.Column(db.String(100), nullable=True)
    timezone = db.Column(db.String(64), nullable=False, default="Asia/Kolkata")
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    registration_date = db.Column(db.DateTime, default=utc_now)

    health_profile = db.relationship(
        "HealthProfile",
        back_populates="user_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )
    cycle_history_logs = db.relationship(
        "CycleHistoryLog",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    symptom_tracking_logs = db.relationship(
        "SymptomTrackingLog",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    medication_reminders = db.relationship(
        "MedicationSupplementReminder",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    ai_sessions = db.relationship(
        "AIHealthAssistantSession",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    forum_posts = db.relationship(
        "ForumPost",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    forum_comments = db.relationship(
        "ForumComment",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    password_reset_tokens = db.relationship(
        "PasswordResetToken",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    daily_logs = db.relationship(
        "DailyLog",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "email": self.email,
            "language_preference": self.language_preference,
            "country": self.country,
            "timezone": self.timezone,
            "onboarding_completed": self.onboarding_completed,
            "role": self.role,
            "registration_date": (
                self.registration_date.isoformat() if self.registration_date else None
            ),
        }
