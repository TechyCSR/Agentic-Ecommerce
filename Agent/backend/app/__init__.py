from flask import Flask

from app.config import get_config
from app.extensions import cors, db, migrate
from app.utils.exceptions import ApiError
from app.utils.responses import error


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    # A distinct version table — this app shares a database with
    # Merchant/backend, which already owns the default `alembic_version`
    # table for its own migration history.
    migrate.init_app(app, db, version_table="alembic_version_agent")
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("FRONTEND_ORIGIN", "*")}},
    )

    register_error_handlers(app)
    register_blueprints(app)

    return app


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return error(exc.code, exc.message, status=exc.status_code, details=exc.details)

    @app.errorhandler(404)
    def handle_404(exc):
        return error("NOT_FOUND", "The requested resource was not found", status=404)

    @app.errorhandler(405)
    def handle_405(exc):
        return error("METHOD_NOT_ALLOWED", "Method not allowed", status=405)

    @app.errorhandler(500)
    def handle_500(exc):
        return error("INTERNAL_SERVER_ERROR", "An unexpected error occurred", status=500)


def register_blueprints(app):
    from app.routes.chat import bp as chat_bp
    from app.routes.health import bp as health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(chat_bp)
