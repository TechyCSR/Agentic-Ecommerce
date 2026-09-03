"""The buyer's address book.

Scoped by Clerk id throughout: every read and write filters on the caller's
own buyer id, so an address can only ever be seen, edited or shipped to by
the account that created it.
"""

from app.extensions import db
from app.models import Address
from app.services import audit_service
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError

REQUIRED = ["full_name", "phone", "line1", "city", "postal_code"]


def list_addresses(buyer_id: str):
    return (
        Address.query.filter_by(buyer_clerk_user_id=buyer_id, is_deleted=False)
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )


def get_default(buyer_id: str):
    addresses = list_addresses(buyer_id)
    if not addresses:
        return None
    return next((a for a in addresses if a.is_default), addresses[0])


def get_for_buyer(buyer_id: str, address_id) -> Address:
    address = Address.query.get(address_id)
    if address is None or address.is_deleted:
        raise NotFoundError("Address not found.", code="ADDRESS_NOT_FOUND")
    if address.buyer_clerk_user_id != buyer_id:
        raise ForbiddenError("You do not have access to this address.", code="ADDRESS_FORBIDDEN")
    return address


def create_address(buyer_id: str, payload: dict) -> Address:
    missing = [f for f in REQUIRED if not (payload.get(f) or "").strip()]
    if missing:
        raise ValidationError(
            f"Missing required field(s): {', '.join(missing)}", code="ADDRESS_INCOMPLETE"
        )

    existing = list_addresses(buyer_id)
    address = Address(
        buyer_clerk_user_id=buyer_id,
        label=(payload.get("label") or "").strip() or None,
        full_name=payload["full_name"].strip(),
        phone=payload["phone"].strip(),
        line1=payload["line1"].strip(),
        line2=(payload.get("line2") or "").strip() or None,
        city=payload["city"].strip(),
        state=(payload.get("state") or "").strip() or None,
        postal_code=payload["postal_code"].strip(),
        country=(payload.get("country") or "India").strip(),
        # First address saved becomes the default, so checkout always has one.
        is_default=bool(payload.get("is_default")) or not existing,
    )
    if address.is_default:
        _clear_defaults(buyer_id)
    db.session.add(address)
    db.session.commit()

    audit_service.log_event(
        action="ADDRESS_ADDED",
        resource_id=address.id,
        buyer_clerk_user_id=buyer_id,
        metadata={"label": address.label, "city": address.city},
    )
    return address


def update_address(buyer_id: str, address_id, payload: dict) -> Address:
    address = get_for_buyer(buyer_id, address_id)
    for field in ["label", "full_name", "phone", "line1", "line2", "city", "state",
                  "postal_code", "country"]:
        if field in payload:
            value = (payload.get(field) or "").strip()
            if field in REQUIRED and not value:
                raise ValidationError(f"{field} can't be empty", code="ADDRESS_INCOMPLETE")
            setattr(address, field, value or None)
    if payload.get("is_default"):
        _clear_defaults(buyer_id)
        address.is_default = True
    db.session.commit()
    return address


def set_default(buyer_id: str, address_id) -> Address:
    address = get_for_buyer(buyer_id, address_id)
    _clear_defaults(buyer_id)
    address.is_default = True
    db.session.commit()
    return address


def delete_address(buyer_id: str, address_id) -> None:
    address = get_for_buyer(buyer_id, address_id)
    # Soft delete: orders snapshot their address, but keeping the row avoids
    # dangling references anywhere else that pointed at it.
    address.is_deleted = True
    address.is_default = False
    db.session.commit()


def _clear_defaults(buyer_id: str):
    Address.query.filter_by(buyer_clerk_user_id=buyer_id, is_deleted=False).update(
        {"is_default": False}
    )
