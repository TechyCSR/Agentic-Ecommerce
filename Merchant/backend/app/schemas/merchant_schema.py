from marshmallow import Schema, fields, validate


class MerchantCreateSchema(Schema):
    business_name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    legal_name = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    email = fields.Email(required=False, allow_none=True)
    phone = fields.String(required=False, allow_none=True)
    website_url = fields.String(required=False, allow_none=True)


class MerchantUpdateSchema(Schema):
    business_name = fields.String(required=False, validate=validate.Length(min=1, max=255))
    legal_name = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    email = fields.Email(required=False, allow_none=True)
    phone = fields.String(required=False, allow_none=True)
    website_url = fields.String(required=False, allow_none=True)
    status = fields.String(
        required=False, validate=validate.OneOf(["ACTIVE", "INACTIVE", "SUSPENDED"])
    )
