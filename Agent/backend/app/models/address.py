from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Address(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A buyer's saved delivery address.

    Scoped by Clerk id like everything else a buyer owns, so one account can
    never read or ship to another's address.
    """

    __tablename__ = "addresses"

    buyer_clerk_user_id = db.Column(db.String(255), nullable=False, index=True)

    label = db.Column(db.String(80), nullable=True)          # Home, Office…
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(40), nullable=False)
    line1 = db.Column(db.String(255), nullable=False)
    line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=True)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(80), nullable=False, default="India")

    is_default = db.Column(db.Boolean, nullable=False, default=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    def one_line(self) -> str:
        parts = [self.line1, self.line2, self.city, self.state, self.postal_code]
        return ", ".join(p for p in parts if p)

    def to_dict(self):
        return {
            "id": str(self.id),
            "label": self.label,
            "full_name": self.full_name,
            "phone": self.phone,
            "line1": self.line1,
            "line2": self.line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_default": self.is_default,
            "one_line": self.one_line(),
        }
