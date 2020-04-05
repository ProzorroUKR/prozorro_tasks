import logging
import urllib3

from flask import Flask
from flask.logging import default_handler
from pythonjsonlogger.jsonlogger import JsonFormatter
from werkzeug.middleware.proxy_fix import ProxyFix

from app.views import bp as app_views_bp
from payments.views import bp as payments_views_bp
from liqpay_int.api import bp as liqpay_resources_bp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, template_folder="templates")

default_handler.setFormatter(JsonFormatter(
    "%(levelname)s %(asctime)s %(module)s %(process)d "
    "%(message)s %(pathname)s $(lineno)d $(funcName)s"
))

logger_root = logging.getLogger()
logger_root.addHandler(default_handler)
logger_root.setLevel(logging.INFO)

app.config.SWAGGER_UI_DOC_EXPANSION = "list"

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2)

app.register_blueprint(app_views_bp)
app.register_blueprint(payments_views_bp, url_prefix="/payments")
app.register_blueprint(liqpay_resources_bp, url_prefix="/liqpay")
