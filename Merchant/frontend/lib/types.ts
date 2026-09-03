export type MerchantStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";
export type StoreStatus = "ACTIVE" | "INACTIVE" | "SUSPENDED";
export type ProductStatus = "DRAFT" | "ACTIVE" | "INACTIVE" | "ARCHIVED";
export type VariantStatus = "ACTIVE" | "OUT_OF_STOCK" | "DISCONTINUED";
export type Availability = "IN_STOCK" | "OUT_OF_STOCK" | "DISCONTINUED";
export type ApiClientType =
  | "INTERNAL_AGENT"
  | "AUTHORIZED_AGENT"
  | "PARTNER"
  | "DEVELOPER";
export type ApiClientStatus = "ACTIVE" | "REVOKED" | "SUSPENDED";
export type ApiScope = "catalog:read" | "product:read";

export interface ApiSuccess<T> {
  success: true;
  data: T;
  meta?: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export interface ApiFailure {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface User {
  id: string;
  clerk_user_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  profile_image_url: string | null;
  role: string;
  created_at: string;
  updated_at: string;
  merchant: Merchant | null;
}

export interface Merchant {
  id: string;
  owner_user_id: string;
  business_name: string;
  legal_name: string | null;
  description: string | null;
  email: string | null;
  phone: string | null;
  website_url: string | null;
  status: MerchantStatus;
  created_at: string;
  updated_at: string;
}

export interface Store {
  id: string;
  merchant_id: string;
  name: string;
  slug: string;
  description: string | null;
  currency: string;
  country: string | null;
  status: StoreStatus;
  created_at: string;
  updated_at: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
  description: string | null;
}

export interface ProductImage {
  id: string;
  product_id: string;
  url: string;
  image_url: string;
  cloudinary_public_id: string | null;
  alt_text: string | null;
  position: number;
  is_primary: boolean;
  created_at: string;
}

export interface ProductVariant {
  id: string;
  variant_id: string;
  product_id: string;
  sku: string;
  name: string;
  price: number;
  currency: string;
  compare_at_price: number | null;
  stock_quantity: number;
  status: VariantStatus;
  availability: Availability;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  store_id: string;
  name: string;
  slug: string;
  short_description: string | null;
  description: string | null;
  brand: string | null;
  status: ProductStatus;
  is_agent_searchable: boolean;
  created_at: string;
  updated_at: string;
  categories: Category[];
  images: ProductImage[];
  variants: ProductVariant[];
  total_stock: number;
}

export interface ApiClient {
  id: string;
  merchant_id: string | null;
  name: string;
  client_type: ApiClientType;
  masked_key: string;
  status: ApiClientStatus;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
}

export interface ApiClientWithKey extends ApiClient {
  api_key: string;
}

export type OrderStatus =
  | "DRAFT"
  | "PENDING_AUTHORIZATION"
  | "AUTHORIZED"
  | "PAYMENT_PENDING"
  | "PAID"
  | "PAYMENT_FAILED"
  | "CANCELLED"
  | "CONFIRMED"
  | "PACKED"
  | "SHIPPED"
  | "DELIVERED";

export type PaymentStatus =
  | "CREATED"
  | "PENDING"
  | "AUTHORIZED"
  | "CAPTURED"
  | "FAILED"
  | "CANCELLED"
  | "REFUNDED";

/** The states a merchant can move a paid order through. */
export const FULFILLMENT_FLOW: OrderStatus[] = [
  "CONFIRMED",
  "PACKED",
  "SHIPPED",
  "DELIVERED",
];

export interface OrderItem {
  id: string;
  order_id: string;
  product_id: string | null;
  product_variant_id: string | null;
  product_name_snapshot: string;
  quantity: number;
  unit_price_amount: number;
  total_amount: number;
}

export interface Payment {
  id: string;
  order_id: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  amount: number;
  currency: string;
  status: PaymentStatus;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  user_id: string | null;
  merchant_id: string;
  store_id: string;
  agent_order_id: string | null;
  buyer_ref: string | null;
  status: OrderStatus;
  payment_status: PaymentStatus | null;
  currency: string;
  subtotal_amount: number;
  tax_amount: number;
  total_amount: number;
  item_count: number;
  placed_at: string | null;
  created_at: string;
  updated_at: string;
  items?: OrderItem[];
  payments?: Payment[];
}

export interface PaymentWithOrder extends Payment {
  order: Order;
}

export interface OrderStats {
  total_orders: number;
  revenue_amount: number;
  currency: string;
  awaiting_fulfillment: number;
  delivered: number;
}
