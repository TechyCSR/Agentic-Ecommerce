from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin

product_categories = db.Table(
    "product_categories",
    db.Column(
        "product_id",
        UUID(as_uuid=True),
        db.ForeignKey("products.id"),
        primary_key=True,
    ),
    db.Column(
        "category_id",
        UUID(as_uuid=True),
        db.ForeignKey("categories.id"),
        primary_key=True,
    ),
    db.Column("is_primary", db.Boolean, nullable=False, default=False),
)


class Category(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "categories"

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)

    parent_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("categories.id"), nullable=True
    )

    description = db.Column(db.Text, nullable=True)

    children = db.relationship(
        "Category", backref=db.backref("parent", remote_side="Category.id")
    )

    products = db.relationship(
        "Product", secondary=product_categories, back_populates="categories"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "description": self.description,
        }
