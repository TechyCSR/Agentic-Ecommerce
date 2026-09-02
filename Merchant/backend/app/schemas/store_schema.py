from marshmallow import Schema, fields, validate


class StoreCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    slug = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    currency = fields.String(required=False, load_default="INR")
    country = fields.String(required=False, allow_none=True)


class StoreUpdateSchema(Schema):
    name = fields.String(required=False, validate=validate.Length(min=1, max=255))
    slug = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    currency = fields.String(required=False)
    country = fields.String(required=False, allow_none=True)
    status = fields.String(
        required=False, validate=validate.OneOf(["ACTIVE", "INACTIVE", "SUSPENDED"])
    )
