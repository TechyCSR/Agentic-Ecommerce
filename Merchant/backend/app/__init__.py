import cloudinary
from flask import Flask

from app.config import get_config
from app.extensions import cors, db, migrate
from app.utils.exceptions import ApiError
from app.utils.responses import error


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config.get("FRONTEND_ORIGIN", "*")}},
    )

    cloudinary.config(
        cloud_name=app.config.get("CLOUDINARY_CLOUD_NAME"),
        api_key=app.config.get("CLOUDINARY_API_KEY"),
        api_secret=app.config.get("CLOUDINARY_API_SECRET"),
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
    from app.routes.admin import bp as admin_bp
    from app.routes.agent import bp as agent_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.catalog import bp as catalog_bp
    from app.routes.categories import bp as categories_bp
    from app.routes.health import bp as health_bp
    from app.routes.merchants import bp as merchants_bp
    from app.routes.orders import bp as orders_bp
    from app.routes.products import bp as products_bp
    from app.routes.stores import bp as stores_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(merchants_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(stores_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)
