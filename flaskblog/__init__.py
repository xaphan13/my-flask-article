from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")

from flaskblog.config import Config

db = SQLAlchemy()
bcrypt = Bcrypt()

login_manager = LoginManager()
login_manager.login_view = "users.login"
login_manager.login_message_category = "info"
login_manager.login_message = "Нужно авторизоваться или зарегистрироваться"


def create_app(config_class=Config, debug_mode=False):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["DEBUG"] = debug_mode
    logFC.info("'create_app 6' app.config:\n" + "\n".join(f"    {k} = {app.config[k]!r}" for k in sorted(app.config)))

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    from flaskblog.new_articles.routes_articles import art_main

    app.register_blueprint(art_main)

    from flaskblog.errors.handlers import errors
    from flaskblog.main.routes_main import main
    from flaskblog.users.routes_users import users

    app.register_blueprint(users)
    app.register_blueprint(main)
    app.register_blueprint(errors)

    logFC.warning("\n\n\n\n'*****************************************************'start 'main()'")
    return app
