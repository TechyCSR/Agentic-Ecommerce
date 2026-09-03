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
  | { type: "product_cards"; cards: ProductCard[] }
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
