import logging

import urllib3

from flask import Flask
from flask.logging import default_handler
from flask_caching import Cache
from pythonjsonlogger.jsonlogger import JsonFormatter

from app.middleware import RequestId
from app.views import bp as app_views_bp
from environment_settings import APP_X_FORWARDED_NUMBER
from payments.views import bp as payments_views_bp
from liqpay_int.api import bp as liqpay_resources_bp
from treasury.api.views import bp as treasury_resources_bp
from werkzeug.middleware.proxy_fix import ProxyFix


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

cache = Cache(config={'CACHE_TYPE': 'simple'})

app = Flask(__name__, template_folder="templates")

cache.init_app(app)

default_handler.setFormatter(JsonFormatter(
    "%(levelname)s %(asctime)s %(module)s %(process)d "
    "%(message)s %(pathname)s $(lineno)d $(funcName)s"
))

logger_root = logging.getLogger()
logger_root.addHandler(default_handler)
logger_root.setLevel(logging.INFO)

app.config.SWAGGER_UI_DOC_EXPANSION = "list"

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=APP_X_FORWARDED_NUMBER)
app.wsgi_app = RequestId(app.wsgi_app)

app.register_blueprint(app_views_bp)
app.register_blueprint(payments_views_bp, url_prefix="/payments")
app.register_blueprint(liqpay_resources_bp, url_prefix="/liqpay")
app.register_blueprint(treasury_resources_bp, url_prefix='/treasury')
