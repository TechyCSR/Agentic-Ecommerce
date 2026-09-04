import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    MERCHANT = "MERCHANT"
    ADMIN = "ADMIN"
    AGENT = "AGENT"


class MerchantStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class StoreStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ProductStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class VariantStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    DISCONTINUED = "DISCONTINUED"


class ApiClientType(str, enum.Enum):
    INTERNAL_AGENT = "INTERNAL_AGENT"
    AUTHORIZED_AGENT = "AUTHORIZED_AGENT"
    PARTNER = "PARTNER"
    DEVELOPER = "DEVELOPER"


class ApiClientStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


class ApiScope(str, enum.Enum):
    CATALOG_READ = "catalog:read"
    PRODUCT_READ = "product:read"
    INVENTORY_READ = "inventory:read"
    CHECKOUT_CREATE = "checkout:create"


ENABLED_SCOPES = [
    ApiScope.CATALOG_READ.value,
    ApiScope.PRODUCT_READ.value,
    # Lets an authorized agent register a paid order against this catalog.
    ApiScope.CHECKOUT_CREATE.value,
]

# Kept as an alias: the original name is referenced elsewhere and in docs.
PHASE1_ENABLED_SCOPES = ENABLED_SCOPES


class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_AUTHORIZATION = "PENDING_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"
    # Fulfillment states, set by the merchant after payment.
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"


# The order a merchant can move an order through, after it is PAID.
FULFILLMENT_FLOW = [
    OrderStatus.CONFIRMED.value,
    OrderStatus.PACKED.value,
    OrderStatus.SHIPPED.value,
    OrderStatus.DELIVERED.value,
]


class ReservationStatus(str, enum.Enum):
    """A stock hold's lifecycle.

    HELD only counts until `expires_at`: availability filters on the
    timestamp, so a hold nobody released stops blocking stock the moment it
    lapses. RELEASED and CONSUMED are the settled outcomes.
    """

    HELD = "HELD"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"


class PaymentProvider(str, enum.Enum):
    RAZORPAY = "RAZORPAY"


class PaymentStatus(str, enum.Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
