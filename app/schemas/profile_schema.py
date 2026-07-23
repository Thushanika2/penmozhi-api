from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.schemas.onboarding_schema import (
    BIRTH_CONTROL_TYPES,
    CONDITION_OPTIONS,
    CYCLE_REGULARITY,
    EXERCISE_FREQUENCIES,
    FLOW_LEVELS,
    STRESS_LEVELS,
    SYMPTOM_OPTIONS,
)


class HealthProfileSettingsSchema(Schema):
    weight = fields.Float(required=False, validate=validate.Range(min=20, max=500))
    height = fields.Float(required=False, validate=validate.Range(min=50, max=300))
    nutritional_needs = fields.Str(required=False, validate=validate.Length(max=500))
    health_risks = fields.Str(required=False, validate=validate.Length(max=500))

    menarche_age = fields.Int(required=False, validate=validate.Range(min=8, max=20))
    average_cycle_length = fields.Int(required=False, validate=validate.Range(min=21, max=45))
    average_period_length = fields.Int(required=False, validate=validate.Range(min=2, max=10))
    last_period_start = fields.Date(required=False, format="%Y-%m-%d")
    typical_flow = fields.Str(required=False, validate=validate.OneOf(FLOW_LEVELS))
    cycle_regularity = fields.Str(required=False, validate=validate.OneOf(CYCLE_REGULARITY))
    common_symptoms = fields.List(fields.Str(), required=False)
    health_conditions = fields.List(fields.Str(), required=False)

    sleep_hours = fields.Float(required=False, validate=validate.Range(min=0, max=24))
    water_intake_liters = fields.Float(required=False, validate=validate.Range(min=0, max=20))
    exercise_frequency = fields.Str(required=False, validate=validate.OneOf(EXERCISE_FREQUENCIES))
    stress_level = fields.Str(required=False, validate=validate.OneOf(STRESS_LEVELS))
    smoking = fields.Bool(required=False)
    alcohol = fields.Bool(required=False)

    trying_to_conceive = fields.Bool(required=False)
    is_pregnant = fields.Bool(required=False)
    is_breastfeeding = fields.Bool(required=False)
    using_birth_control = fields.Bool(required=False)
    birth_control_type = fields.Str(required=False, validate=validate.OneOf(BIRTH_CONTROL_TYPES))

    notify_period = fields.Bool(required=False)
    notify_ovulation = fields.Bool(required=False)
    notify_medication = fields.Bool(required=False)
    notify_daily_health = fields.Bool(required=False)

    @validates_schema
    def validate_lists(self, data, **_kwargs):
        if "common_symptoms" in data:
            invalid = [item for item in data["common_symptoms"] if item not in SYMPTOM_OPTIONS]
            if invalid:
                raise ValidationError({"common_symptoms": [f"Invalid symptom: {item}" for item in invalid]})

        if "health_conditions" in data:
            invalid = [item for item in data["health_conditions"] if item not in CONDITION_OPTIONS]
            if invalid:
                raise ValidationError(
                    {"health_conditions": [f"Invalid condition: {item}" for item in invalid]}
                )
