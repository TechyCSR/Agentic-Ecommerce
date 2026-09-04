import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://agentic:agentic@localhost:5432/agentic_commerce"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Clerk (JWT verification only — this service never calls the Clerk
    # backend API, so no CLERK_SECRET_KEY is needed here)
    CLERK_ISSUER = os.getenv("CLERK_ISSUER", "")
    CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") or (
        f"{os.getenv('CLERK_ISSUER', '')}/.well-known/jwks.json"
    )

    # Merchant Phase 1 agent API — the sole source of product truth
    MERCHANT_AGENT_API_URL = os.getenv(
        "MERCHANT_AGENT_API_URL", "http://localhost:5000"
    )
    MERCHANT_AGENT_API_KEY = os.getenv("MERCHANT_AGENT_API_KEY", "")

    # LLM — any OpenAI-compatible chat completions endpoint
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.bluesminds.com/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

    # Razorpay (Test Mode). The secret stays server-side — only the key id
    # is ever sent to the browser, and only to open Checkout.
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    # Set in the Razorpay dashboard when creating the webhook. Distinct
    # from the API key secret, and signs the raw webhook body.
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # Upper bound on a single order, in the smallest currency unit (paise).
    # Razorpay enforces its own per-account/per-method ceiling and rejects
    # the payment inside Checkout with "Amount exceeds maximum amount
    # allowed" — which the buyer only discovers after clicking Pay. Setting
    # this to your account's real limit turns that into a clear message at
    # checkout instead. 0 disables the app-side check.
    MAX_ORDER_AMOUNT = int(os.getenv("MAX_ORDER_AMOUNT", "0"))

    # How long to ask the Merchant service to hold a priced order's stock.
    # It caps this at 60 minutes; the window only needs to cover a buyer
    # walking through Razorpay Checkout.
    STOCK_RESERVATION_TTL_MINUTES = int(
        os.getenv("STOCK_RESERVATION_TTL_MINUTES", "15")
    )

    # Telegram channel — the bot token talks to Telegram's API, the webhook
    # secret authenticates updates arriving from it.
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    # Where Telegram sends buyers to complete payment (the deployed web app).
    AGENT_WEB_URL = os.getenv("AGENT_WEB_URL", "http://localhost:3100")

    # CORS
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3100")

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
