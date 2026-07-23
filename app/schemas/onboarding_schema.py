from marshmallow import Schema, ValidationError, fields, validate, validates_schema

FLOW_LEVELS = ("light", "medium", "heavy", "very_heavy")
CYCLE_REGULARITY = ("regular", "irregular")
SYMPTOM_OPTIONS = (
    "cramps",
    "headache",
    "acne",
    "back_pain",
    "mood_swings",
    "tender_breasts",
    "fatigue",
    "bloating",
    "nausea",
    "cravings",
    "no_symptoms",
)
CONDITION_OPTIONS = (
    "pcos",
    "endometriosis",
    "fibroids",
    "anemia",
    "thyroid",
    "diabetes",
    "hypertension",
    "migraine",
    "depression",
    "anxiety",
    "none",
)
EXERCISE_FREQUENCIES = ("never", "rarely", "weekly", "daily")
STRESS_LEVELS = ("low", "medium", "high")
BIRTH_CONTROL_TYPES = (
    "none",
    "pill",
    "iud",
    "implant",
    "injection",
    "condom",
    "other",
)


class OnboardingSchema(Schema):
    # Step 1 — Basic information
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    date_of_birth = fields.Date(required=True, format="%Y-%m-%d")
    country = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    height = fields.Float(required=True, validate=validate.Range(min=50, max=300))
    weight = fields.Float(required=True, validate=validate.Range(min=20, max=500))
    language_preference = fields.Str(required=True)
    timezone = fields.Str(required=True, validate=validate.Length(max=64))

    # Step 2 — Menstrual information
    menarche_age = fields.Int(required=True, validate=validate.Range(min=8, max=20))
    average_cycle_length = fields.Int(required=True, validate=validate.Range(min=21, max=45))
    average_period_length = fields.Int(required=True, validate=validate.Range(min=2, max=10))
    last_period_start = fields.Date(required=True, format="%Y-%m-%d")
    typical_flow = fields.Str(required=True, validate=validate.OneOf(FLOW_LEVELS))
    cycle_regularity = fields.Str(required=True, validate=validate.OneOf(CYCLE_REGULARITY))

    # Step 3 & 4 — Multi-select
    common_symptoms = fields.List(fields.Str(), required=True)
    health_conditions = fields.List(fields.Str(), required=True)

    # Step 5 — Lifestyle
    sleep_hours = fields.Float(required=True, validate=validate.Range(min=0, max=24))
    water_intake_liters = fields.Float(required=True, validate=validate.Range(min=0, max=20))
    exercise_frequency = fields.Str(required=True, validate=validate.OneOf(EXERCISE_FREQUENCIES))
    stress_level = fields.Str(required=True, validate=validate.OneOf(STRESS_LEVELS))
    smoking = fields.Bool(required=True)
    alcohol = fields.Bool(required=True)

    # Step 6 — Pregnancy
    trying_to_conceive = fields.Bool(required=True)
    is_pregnant = fields.Bool(required=True)
    is_breastfeeding = fields.Bool(required=True)
    using_birth_control = fields.Bool(required=True)
    birth_control_type = fields.Str(load_default="none")

    # Step 7 — Notifications
    notify_period = fields.Bool(required=True)
    notify_ovulation = fields.Bool(required=True)
    notify_medication = fields.Bool(required=True)
    notify_daily_health = fields.Bool(required=True)

    @validates_schema
    def validate_multi_select(self, data, **_kwargs):
        symptoms = data.get("common_symptoms", [])
        invalid_symptoms = [item for item in symptoms if item not in SYMPTOM_OPTIONS]
        if invalid_symptoms:
            raise ValidationError(
                {"common_symptoms": [f"Invalid symptom: {item}" for item in invalid_symptoms]}
            )

        conditions = data.get("health_conditions", [])
        invalid_conditions = [item for item in conditions if item not in CONDITION_OPTIONS]
        if invalid_conditions:
            raise ValidationError(
                {
                    "health_conditions": [
                        f"Invalid condition: {item}" for item in invalid_conditions
                    ]
                }
            )

        if data.get("using_birth_control") and not data.get("birth_control_type"):
            raise ValidationError(
                {"birth_control_type": ["birth_control_type is required when using birth control."]}
            )

        if data.get("birth_control_type") not in BIRTH_CONTROL_TYPES:
            raise ValidationError(
                {"birth_control_type": ["Invalid birth control type."]}
            )
