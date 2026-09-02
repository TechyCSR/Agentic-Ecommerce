from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.category import product_categories
from app.models.enums import ProductStatus


class Product(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "products"

    store_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("stores.id"), nullable=False, index=True
    )

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, index=True)

    short_description = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)

    brand = db.Column(db.String(255), nullable=True, index=True)

    status = db.Column(
        SAEnum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.DRAFT,
        index=True,
    )
    is_agent_searchable = db.Column(db.Boolean, nullable=False, default=True)

    store = db.relationship("Store", back_populates="products")
    variants = db.relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.created_at",
    )
    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    categories = db.relationship(
        "Category", secondary=product_categories, back_populates="products"
    )

    __table_args__ = (
        db.UniqueConstraint("store_id", "slug", name="uq_products_store_slug"),
    )

    @property
    def primary_image(self):
        for image in self.images:
            if image.is_primary:
                return image
        return self.images[0] if self.images else None

    @property
    def primary_category(self):
        return self.categories[0] if self.categories else None

    @property
    def total_stock(self):
        return sum(v.stock_quantity or 0 for v in self.variants)

    def to_dict(self, include_relations=True):
        data = {
            "id": str(self.id),
            "store_id": str(self.store_id),
            "name": self.name,
            "slug": self.slug,
            "short_description": self.short_description,
            "description": self.description,
            "brand": self.brand,
            "status": self.status.value if self.status else None,
            "is_agent_searchable": self.is_agent_searchable,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_relations:
            data["categories"] = [c.to_dict() for c in self.categories]
            data["images"] = [i.to_dict() for i in self.images]
            data["variants"] = [v.to_dict() for v in self.variants]
            data["total_stock"] = self.total_stock
        return data
