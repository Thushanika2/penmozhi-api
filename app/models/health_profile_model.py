from app.extensions import db
from app.utils import utc_now


class HealthProfile(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(
        db.Integer,
        db.ForeignKey("user_profiles.id"),
        nullable=False,
        unique=True,
    )
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    calculated_bmi = db.Column(db.Float, nullable=True)
    nutritional_needs = db.Column(db.String(500), nullable=True)
    health_risks = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    user_profile = db.relationship("UserProfile", back_populates="health_profile")
    pcos_disorder_statuses = db.relationship(
        "PCOSDisorderStatus",
        back_populates="health_profile",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "weight": self.weight,
            "height": self.height,
            "calculated_bmi": self.calculated_bmi,
            "nutritional_needs": self.nutritional_needs,
            "health_risks": self.health_risks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
