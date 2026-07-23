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

    # Menstrual baseline (Step 2)
    menarche_age = db.Column(db.Integer, nullable=True)
    average_cycle_length = db.Column(db.Integer, nullable=True, default=28)
    average_period_length = db.Column(db.Integer, nullable=True, default=5)
    last_period_start = db.Column(db.Date, nullable=True)
    typical_flow = db.Column(db.String(20), nullable=True)
    cycle_regularity = db.Column(db.String(20), nullable=True)

    # Multi-select stored as JSON arrays
    common_symptoms = db.Column(db.JSON, nullable=True)
    health_conditions = db.Column(db.JSON, nullable=True)

    # Lifestyle (Step 5)
    sleep_hours = db.Column(db.Float, nullable=True)
    water_intake_liters = db.Column(db.Float, nullable=True)
    exercise_frequency = db.Column(db.String(30), nullable=True)
    stress_level = db.Column(db.String(20), nullable=True)
    smoking = db.Column(db.Boolean, nullable=False, default=False)
    alcohol = db.Column(db.Boolean, nullable=False, default=False)

    # Pregnancy & birth control (Step 6)
    trying_to_conceive = db.Column(db.Boolean, nullable=False, default=False)
    is_pregnant = db.Column(db.Boolean, nullable=False, default=False)
    is_breastfeeding = db.Column(db.Boolean, nullable=False, default=False)
    using_birth_control = db.Column(db.Boolean, nullable=False, default=False)
    birth_control_type = db.Column(db.String(50), nullable=True)

    # Notification preferences (Step 7)
    notify_period = db.Column(db.Boolean, nullable=False, default=True)
    notify_ovulation = db.Column(db.Boolean, nullable=False, default=True)
    notify_medication = db.Column(db.Boolean, nullable=False, default=True)
    notify_daily_health = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

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
            "menarche_age": self.menarche_age,
            "average_cycle_length": self.average_cycle_length,
            "average_period_length": self.average_period_length,
            "last_period_start": (
                self.last_period_start.isoformat() if self.last_period_start else None
            ),
            "typical_flow": self.typical_flow,
            "cycle_regularity": self.cycle_regularity,
            "common_symptoms": self.common_symptoms or [],
            "health_conditions": self.health_conditions or [],
            "sleep_hours": self.sleep_hours,
            "water_intake_liters": self.water_intake_liters,
            "exercise_frequency": self.exercise_frequency,
            "stress_level": self.stress_level,
            "smoking": self.smoking,
            "alcohol": self.alcohol,
            "trying_to_conceive": self.trying_to_conceive,
            "is_pregnant": self.is_pregnant,
            "is_breastfeeding": self.is_breastfeeding,
            "using_birth_control": self.using_birth_control,
            "birth_control_type": self.birth_control_type,
            "notify_period": self.notify_period,
            "notify_ovulation": self.notify_ovulation,
            "notify_medication": self.notify_medication,
            "notify_daily_health": self.notify_daily_health,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
