from marshmallow import Schema, fields, validate

FLOW_LEVELS = ("none", "spotting", "light", "medium", "heavy")
PAIN_LEVELS = ("none", "mild", "moderate", "severe")
ENERGY_LEVELS = ("low", "medium", "high")
CERVICAL_FLUID = ("dry", "sticky", "creamy", "egg_white")
EXERCISE_LEVELS = ("none", "light", "moderate", "intense")


class DailyLogSchema(Schema):
    log_date = fields.Date(required=True, format="%Y-%m-%d")
    flow_level = fields.Str(load_default="none", validate=validate.OneOf(FLOW_LEVELS))
    pain_level = fields.Str(load_default="none", validate=validate.OneOf(PAIN_LEVELS))
    mood = fields.Str(required=False, allow_none=True, validate=validate.Length(max=50))
    energy = fields.Str(required=False, allow_none=True, validate=validate.OneOf(ENERGY_LEVELS))
    sleep_hours = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0, max=24))
    exercise = fields.Str(required=False, allow_none=True, validate=validate.OneOf(EXERCISE_LEVELS))
    weight = fields.Float(required=False, allow_none=True, validate=validate.Range(min=20, max=500))
    basal_temp = fields.Float(required=False, allow_none=True, validate=validate.Range(min=35, max=42))
    cervical_fluid = fields.Str(required=False, allow_none=True, validate=validate.OneOf(CERVICAL_FLUID))
    sexual_activity = fields.Bool(load_default=False)
    notes = fields.Str(required=False, allow_none=True)


class DailyLogUpdateSchema(DailyLogSchema):
    log_date = fields.Date(required=False, format="%Y-%m-%d")
