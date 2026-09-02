from marshmallow import ValidationError as MarshmallowValidationError

from app.utils.exceptions import ValidationError


def validate_payload(schema, data):
    try:
        return schema.load(data or {})
    except MarshmallowValidationError as exc:
        raise ValidationError(
            "Request validation failed", details=exc.messages
        ) from exc
