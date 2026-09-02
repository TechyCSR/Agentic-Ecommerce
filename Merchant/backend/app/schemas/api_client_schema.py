from marshmallow import Schema, fields, validate


class ApiClientCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    client_type = fields.String(
        required=False,
        validate=validate.OneOf(
            ["INTERNAL_AGENT", "AUTHORIZED_AGENT", "PARTNER", "DEVELOPER"]
        ),
    )
    scopes = fields.List(
        fields.String(validate=validate.OneOf(["catalog:read", "product:read"])),
        required=False,
    )
