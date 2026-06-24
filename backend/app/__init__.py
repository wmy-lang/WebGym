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


def _register_blueprints(app: Flask) -> None:
    from .api.ping import bp as ping_bp

    app.register_blueprint(ping_bp, url_prefix="/api")


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def _not_found(_e):
        return jsonify(error="not_found"), 404

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return jsonify(error="method_not_allowed"), 405
