from marshmallow import Schema, fields, validate


class ProductVariantSchema(Schema):
    sku = fields.String(required=True, validate=validate.Length(min=1, max=120))
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    price = fields.Integer(required=True, validate=validate.Range(min=0))
    currency = fields.String(required=False)
    compare_at_price = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))
    stock_quantity = fields.Integer(required=False, validate=validate.Range(min=0), load_default=0)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["ACTIVE", "OUT_OF_STOCK", "DISCONTINUED"]),
    )


class ProductImageSchema(Schema):
    image_url = fields.String(required=True)
    cloudinary_public_id = fields.String(required=False, allow_none=True)
    alt_text = fields.String(required=False, allow_none=True)
    position = fields.Integer(required=False)
    is_primary = fields.Boolean(required=False)


class ProductCreateSchema(Schema):
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    slug = fields.String(required=False, allow_none=True)
    short_description = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    brand = fields.String(required=False, allow_none=True)
    category_ids = fields.List(fields.String(), required=False)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["DRAFT", "ACTIVE", "INACTIVE", "ARCHIVED"]),
    )
    is_agent_searchable = fields.Boolean(required=False, load_default=True)
    variants = fields.List(fields.Nested(ProductVariantSchema), required=False)
    images = fields.List(fields.Nested(ProductImageSchema), required=False)


class ProductUpdateSchema(Schema):
    name = fields.String(required=False, validate=validate.Length(min=1, max=255))
    slug = fields.String(required=False, allow_none=True)
    short_description = fields.String(required=False, allow_none=True)
    description = fields.String(required=False, allow_none=True)
    brand = fields.String(required=False, allow_none=True)
    category_ids = fields.List(fields.String(), required=False)
    status = fields.String(
        required=False,
        validate=validate.OneOf(["DRAFT", "ACTIVE", "INACTIVE", "ARCHIVED"]),
    )
    is_agent_searchable = fields.Boolean(required=False)


class VariantUpdateSchema(Schema):
    name = fields.String(required=False)
    price = fields.Integer(required=False, validate=validate.Range(min=0))
    currency = fields.String(required=False)
    compare_at_price = fields.Integer(required=False, allow_none=True, validate=validate.Range(min=0))
    stock_quantity = fields.Integer(required=False, validate=validate.Range(min=0))
    status = fields.String(
        required=False,
        validate=validate.OneOf(["ACTIVE", "OUT_OF_STOCK", "DISCONTINUED"]),
    )
