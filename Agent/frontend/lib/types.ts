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

export type SelectionStatus = "SELECTED" | "SUPERSEDED";

export interface Selection {
  id: string;
  session_id: string;
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  merchant_name: string | null;
  price: Money;
  status: SelectionStatus;
  created_at: string;
}
