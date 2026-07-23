from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class RegisterSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=255))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))
    date_of_birth = fields.Date(required=True, format="%Y-%m-%d")
    language_preference = fields.Str(load_default="english")


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.Str(required=True, validate=validate.Length(min=10))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))


class RefreshTokenSchema(Schema):
    refresh_token = fields.Str(required=True)


class UpdateProfileSchema(Schema):
    language_preference = fields.Str(required=False)
    full_name = fields.Str(required=False, validate=validate.Length(min=2, max=255))
    country = fields.Str(required=False, validate=validate.Length(max=100))
    timezone = fields.Str(required=False, validate=validate.Length(max=64))
