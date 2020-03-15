from flask import Flask
from app.views import bp as app_views_bp
from payments.views import bp as payments_views_bp
from liqpay_int.resources import bp as liqpay_resources_bp

app = Flask(__name__, template_folder="templates")

app.register_blueprint(app_views_bp)
app.register_blueprint(payments_views_bp, url_prefix="/payments")
app.register_blueprint(liqpay_resources_bp, url_prefix="/liqpay")
