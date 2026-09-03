from marshmallow import Schema, fields, validate

from app.models.enums import ENABLED_SCOPES


class ApiClientCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    client_type = fields.String(
        required=False,
        validate=validate.OneOf(
            ["INTERNAL_AGENT", "AUTHORIZED_AGENT", "PARTNER", "DEVELOPER"]
        ),
    )
    scopes = fields.List(
        fields.String(validate=validate.OneOf(ENABLED_SCOPES)),
        required=False,
    )
