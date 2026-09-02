from app.extensions import db
from app.models import Category
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.slugify import unique_slug


def _slug_exists(candidate):
    return Category.query.filter_by(slug=candidate).first() is not None


def list_categories():
    return Category.query.order_by(Category.name).all()


def get_category_or_404(category_id):
    category = Category.query.get(category_id)
    if not category:
        raise NotFoundError("Category not found", code="CATEGORY_NOT_FOUND")
    return category


def create_category(payload):
    name = payload.get("name")
    if not name:
        raise ValidationError("Category name is required")

    slug = unique_slug(payload.get("slug") or name, _slug_exists)

    category = Category(
        name=name,
        slug=slug,
        parent_id=payload.get("parent_id"),
        description=payload.get("description"),
    )
    db.session.add(category)
    db.session.commit()
    return category


def resolve_categories(category_ids):
    if not category_ids:
        return []
    categories = Category.query.filter(Category.id.in_(category_ids)).all()
    found_ids = {str(c.id) for c in categories}
    missing = [cid for cid in category_ids if str(cid) not in found_ids]
    if missing:
        raise ValidationError(f"Unknown category id(s): {missing}")
    return categories
