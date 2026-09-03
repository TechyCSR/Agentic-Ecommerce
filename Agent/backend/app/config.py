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
