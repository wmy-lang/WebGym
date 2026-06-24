"""应用工厂。对照 Spring Boot 的 ``SpringApplication.run``：
集中完成配置加载、扩展绑定、蓝图注册、错误处理注册。
"""
from __future__ import annotations

from flask import Flask, jsonify

from .config import INSTANCE_DIR, get_config
from .extensions import cors, csrf, db, login_manager, migrate


def create_app(config_name: str | None = None) -> Flask:
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, instance_path=str(INSTANCE_DIR))
    cfg = get_config(config_name)
    app.config.from_object(cfg)
    app.config["ENV_NAME"] = cfg.__name__.replace("Config", "").lower()

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"],
    )

    login_manager.login_view = None  # API 模式：未登录返回 401，不重定向

    @login_manager.unauthorized_handler
    def _unauthorized():
        return jsonify(error="unauthorized"), 401

    # 注册 user_loader；放在这里以避免 models 被全局导入时绑不上 login_manager
    from . import models  # noqa: F401  确保 metadata 完整

    @login_manager.user_loader
    def _load_user(user_id: str):
        return db.session.get(models.User, int(user_id))


def _register_blueprints(app: Flask) -> None:
    from .api.attendance import bp as attendance_bp
    from .api.auth import bp as auth_bp
    from .api.bookings import bp as bookings_bp
    from .api.card_types import bp as card_types_bp
    from .api.cards import bp as cards_bp
    from .api.classes import bp as classes_bp
    from .api.coaches import bp as coaches_bp
    from .api.members import bp as members_bp
    from .api.ping import bp as ping_bp
    from .api.sessions import bp as sessions_bp

    app.register_blueprint(ping_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(members_bp, url_prefix="/api/members")
    app.register_blueprint(coaches_bp, url_prefix="/api/coaches")
    app.register_blueprint(card_types_bp, url_prefix="/api/card-types")
    app.register_blueprint(cards_bp, url_prefix="/api/cards")
    app.register_blueprint(classes_bp, url_prefix="/api/classes")
    app.register_blueprint(sessions_bp, url_prefix="/api/sessions")
    app.register_blueprint(bookings_bp, url_prefix="/api/bookings")
    app.register_blueprint(attendance_bp, url_prefix="/api/attendance")


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify(error="method_not_allowed"), 405


def _register_cli(app: Flask) -> None:
    from .cli import register_cli

    register_cli(app)
