const CURRENCY_LOCALE: Record<string, string> = {
  INR: "en-IN",
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
};

export function formatMoney(amountInSmallestUnit: number, currency = "INR") {
  const locale = CURRENCY_LOCALE[currency] || "en-IN";
  const major = amountInSmallestUnit / 100;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(major);
}
