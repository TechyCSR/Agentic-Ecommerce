from app.extensions import db
from app.models import Merchant
from app.services import audit_service
from app.utils.exceptions import ConflictError, ForbiddenError, NotFoundError


def create_merchant(user, payload):
    existing = Merchant.query.filter_by(owner_user_id=user.id).first()
    if existing:
        raise ConflictError(
            "This user already owns a merchant profile", code="MERCHANT_EXISTS"
        )

    merchant = Merchant(
        owner_user_id=user.id,
        business_name=payload["business_name"],
        legal_name=payload.get("legal_name"),
        description=payload.get("description"),
        email=payload.get("email"),
        phone=payload.get("phone"),
        website_url=payload.get("website_url"),
    )
    db.session.add(merchant)
    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=merchant.id,
        resource_type="MERCHANT",
        resource_id=merchant.id,
        action="MERCHANT_CREATED",
        metadata={"business_name": merchant.business_name},
    )
    return merchant


def get_merchant_for_user(user):
    merchant = Merchant.query.filter_by(owner_user_id=user.id).first()
    if not merchant:
        raise NotFoundError(
            "No merchant profile found for this user", code="MERCHANT_NOT_FOUND"
        )
    return merchant


def update_merchant(user, payload):
    merchant = get_merchant_for_user(user)

    for field in [
        "business_name",
        "legal_name",
        "description",
        "email",
        "phone",
        "website_url",
        "status",
    ]:
        if field in payload and payload[field] is not None:
            setattr(merchant, field, payload[field])

    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=merchant.id,
        resource_type="MERCHANT",
        resource_id=merchant.id,
        action="MERCHANT_UPDATED",
        metadata=payload,
    )
    return merchant


def assert_owns_merchant(user, merchant):
    if merchant.owner_user_id != user.id:
        raise ForbiddenError(
            "You do not have access to this merchant", code="MERCHANT_FORBIDDEN"
        )
