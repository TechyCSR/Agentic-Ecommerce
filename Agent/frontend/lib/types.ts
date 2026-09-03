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

export type MessageRole = "user" | "assistant";

export interface Money {
  amount: number;
  currency: string;
}

export interface ProductCardVariant {
  variant_id: string;
  name: string;
  sku: string | null;
  price: Money | null;
  availability: "IN_STOCK" | "OUT_OF_STOCK" | "DISCONTINUED" | null;
  stock_quantity: number | null;
}

export interface ProductCard {
  product_id: string;
  name: string;
  brand: string | null;
  category: string | null;
  description: string | null;
  image_url: string | null;
  /** Primary first, then the rest — served with the product, never fetched separately. */
  images?: string[];
  merchant_name: string | null;
  store_name: string | null;
  price: Money | null;
  availability: "IN_STOCK" | "OUT_OF_STOCK" | "DISCONTINUED" | null;
  variants: ProductCardVariant[];
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  product_cards: ProductCard[] | null;
  suggested_replies: string[] | null;
  /** A priced order this turn prepared — renders a Pay button. */
  prepared_checkout: PreparedCheckout | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: ChatMessage[];
}

export type SelectionStatus = "SELECTED" | "SUPERSEDED" | "REMOVED";

export interface CartItem {
  id: string;
  session_id: string;
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  merchant_name: string | null;
  price: Money;
  image_url: string | null;
  quantity: number;
  line_total: Money;
  status: SelectionStatus;
  created_at: string;
}

export interface Cart {
  items: CartItem[];
  total: Money;
}

export type OrderStatus = "CREATED" | "CONFIRMED" | "CANCELLED";

export type PaymentStatus =
  | "CREATED"
  | "PENDING"
  | "AUTHORIZED"
  | "PAID"
  | "FAILED"
  | "CANCELLED";

export interface OrderItem {
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string | null;
  merchant_name: string | null;
  image_url: string | null;
  quantity: number;
  unit_price: Money;
  line_total: Money;
}

export interface PaymentRecord {
  id: string;
  order_id: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  amount: number;
  currency: string;
  status: PaymentStatus;
  failure_reason: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface Order {
  id: string;
  session_id: string | null;
  items: OrderItem[];
  amount_total: number;
  currency: string;
  total: Money;
  status: OrderStatus;
  payment_status: PaymentStatus | null;
  payments?: PaymentRecord[];
  created_at: string;
  confirmed_at: string | null;
}

/** What the backend returns when the user explicitly authorizes payment.
 * Contains the public key id only — never the Razorpay secret. */
export interface PaymentAuthorization {
  payment_id: string;
  provider_order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  order: Order;
}

export interface PreparedCheckout {
  order_id: string;
  amount: number;
  currency: string;
  items: OrderItem[];
}

export interface Receipt {
  order_id: string;
  items: OrderItem[];
  total: Money;
  order_status: OrderStatus;
  payment_status: PaymentStatus;
  payment_id: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface Address {
  id: string;
  label: string | null;
  full_name: string;
  phone: string;
  line1: string;
  line2: string | null;
  city: string;
  state: string | null;
  postal_code: string;
  country: string;
  is_default: boolean;
  one_line: string;
}

export type AddressPayload = {
  label?: string;
  full_name: string;
  phone: string;
  line1: string;
  line2?: string;
  city: string;
  state?: string;
  postal_code: string;
};

/** One money action from the audit trail, scoped to the signed-in buyer. */
export interface AuditEntry {
  id: string;
  action: string;
  order_id: string | null;
  amount: number | null;
  currency: string | null;
  status: string | null;
  reason: string | null;
  created_at: string;
}

// SSE event shapes streamed from POST /sessions/:id/messages
export type ToolArgs = Record<string, string | number | boolean | null>;

export type StreamEvent =
  | { type: "thinking" }
  | { type: "tool_start"; tool: string; label?: string }
  | {
      type: "tool_end";
      tool: string;
      result_count?: number;
      error?: boolean;
      args?: ToolArgs;
      product_name?: string;
    }
  | { type: "token"; delta: string }
  /** Discard streamed text so far — it turned out to precede a tool call. */
  | { type: "retract" }
  | { type: "product_cards"; cards: ProductCard[] }
  /** The agent priced an order; the buyer must still authorize payment. */
  | { type: "checkout_ready"; order: PreparedCheckout }
  | { type: "suggestions"; items: string[] }
  | { type: "done"; message_id: string }
  | { type: "error"; message: string };

/** One line in the agent activity timeline, derived only from real stream events. */
export interface ActivityStep {
  id: string;
  kind: "thinking" | "tool";
  tool?: string;
  label: string;
  detail?: string;
  args?: ToolArgs;
  resultCount?: number;
  status: "running" | "done" | "error";
}
