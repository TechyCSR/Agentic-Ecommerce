/** Razorpay Checkout loader.
 *
 * The script is fetched once per page and reused. Only the public key id
 * and the provider order id ever reach this code — the key secret stays on
 * the backend, and the result of checkout is treated as an unverified claim
 * until the backend verifies its signature.
 */

const SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

export interface RazorpaySuccess {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayInstance {
  open: () => void;
  on: (event: string, handler: (payload: RazorpayFailurePayload) => void) => void;
}

interface RazorpayFailurePayload {
  error?: { code?: string; description?: string; reason?: string };
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => RazorpayInstance;
  }
}

let loader: Promise<void> | null = null;

export function loadRazorpay(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("No window"));
  if (window.Razorpay) return Promise.resolve();
  if (loader) return loader;

  loader = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Razorpay")));
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loader = null;
      reject(new Error("Couldn't load the payment window. Check your connection."));
    };
    document.body.appendChild(script);
  });

  return loader;
}

export async function openRazorpayCheckout(options: {
  keyId: string;
  providerOrderId: string;
  amount: number;
  currency: string;
  description?: string;
  prefill?: { name?: string; email?: string };
  onSuccess: (response: RazorpaySuccess) => void;
  onDismiss: () => void;
  onFailure: (reason: string) => void;
}): Promise<void> {
  await loadRazorpay();
  if (!window.Razorpay) throw new Error("Payment window unavailable");

  const rzp = new window.Razorpay({
    key: options.keyId,
    amount: options.amount,
    currency: options.currency,
    order_id: options.providerOrderId,
    name: "Agentic Commerce",
    description: options.description || "Order payment",
    prefill: options.prefill,
    theme: { color: "#111111" },
    handler: options.onSuccess,
    modal: { ondismiss: options.onDismiss },
  });

  rzp.on("payment.failed", (payload) => {
    options.onFailure(
      payload?.error?.description || payload?.error?.reason || "Payment failed"
    );
  });

  rzp.open();
}
