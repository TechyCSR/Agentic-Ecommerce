from app.extensions import db
from app.models import Store
from app.services import audit_service
from app.services.merchant_service import assert_owns_merchant, get_merchant_for_user
from app.utils.exceptions import NotFoundError
from app.utils.slugify import unique_slug


def _slug_exists(candidate):
    return Store.query.filter_by(slug=candidate).first() is not None


def create_store(user, payload):
    merchant = get_merchant_for_user(user)

    slug = payload.get("slug") or payload["name"]
    slug = unique_slug(slug, _slug_exists)

    store = Store(
        merchant_id=merchant.id,
        name=payload["name"],
        slug=slug,
        description=payload.get("description"),
        currency=payload.get("currency", "INR"),
        country=payload.get("country"),
    )
    db.session.add(store)
    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=merchant.id,
        resource_type="STORE",
        resource_id=store.id,
        action="STORE_CREATED",
        metadata={"name": store.name, "slug": store.slug},
    )
    return store


def list_stores_for_user(user):
    merchant = get_merchant_for_user(user)
    return Store.query.filter_by(merchant_id=merchant.id).order_by(
        Store.created_at.desc()
    ).all()


def get_store_or_404(store_id):
    store = Store.query.get(store_id)
    if not store:
        raise NotFoundError("Store not found", code="STORE_NOT_FOUND")
    return store


def get_store_for_user(user, store_id):
    store = get_store_or_404(store_id)
    assert_owns_merchant(user, store.merchant)
    return store


def update_store(user, store_id, payload):
    store = get_store_for_user(user, store_id)

    for field in ["name", "description", "currency", "country", "status"]:
        if field in payload and payload[field] is not None:
            setattr(store, field, payload[field])

    if payload.get("slug") and payload["slug"] != store.slug:
        new_slug = unique_slug(payload["slug"], _slug_exists)
        store.slug = new_slug

    db.session.commit()

    audit_service.log_event(
        actor_type="USER",
        actor_id=user.id,
        merchant_id=store.merchant_id,
        resource_type="STORE",
        resource_id=store.id,
        action="STORE_UPDATED",
        metadata=payload,
    )
    return store
