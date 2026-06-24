"""Flask 扩展实例化（对应 Spring `@Configuration` Bean）。

集中持有扩展单例，避免循环导入；具体绑定在 ``create_app`` 中完成。
"""
from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
cors = CORS()
