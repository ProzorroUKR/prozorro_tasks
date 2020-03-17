from flask import Blueprint, jsonify
from flask_restful import Resource, reqparse
from liqpay.liqpay3 import LiqPay

from app.api import Api
from app.auth import login_group_required, ip_group_required
from environment_settings import LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY
from liqpay_int.exceptions import LiqpayResponseError
from liqpay_int.utils import generate_checkout_params
from celery_worker.celery import app as celery_app


API_VERSION = 1

bp = Blueprint('payments_resources', __name__)
api = Api(bp, prefix="/api/v{}".format(API_VERSION))

parser_push = reqparse.RequestParser()
parser_push.add_argument('type', location="json")
parser_push.add_argument('date_oper', location="json")
parser_push.add_argument('amount', location="json", required=True)
parser_push.add_argument('currency', location="json", required=True)
parser_push.add_argument('okpo', location="json")
parser_push.add_argument('mfo', location="json")
parser_push.add_argument('name', location="json")
parser_push.add_argument('description', location="json", required=True)

parser_checkout = reqparse.RequestParser()
parser_push.add_argument('amount', location="json", required=True)
parser_push.add_argument('currency', location="json", required=True)
parser_push.add_argument('description', location="json", required=True)
parser_push.add_argument('language', location="json")
parser_push.add_argument('result_url', location="json")


class PushResource(Resource):
    method_decorators = {
        'post': [ip_group_required("payment_providers")]
    }

    def post(self):
        celery_app.send_task('payments.process_payment', kwargs=dict(payment_data=parser_push.parse_args()))
        return jsonify({"status": "success"})


class CheckoutResource(Resource):
    method_decorators = {
        'post': [login_group_required("brokers")]
    }

    def post(self):
        params = generate_checkout_params(parser_checkout.parse_args())
        liqpay = LiqPay(LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY)
        try:
            resp_json = liqpay.api("/request", params)
        except Exception as ex:
            raise LiqpayResponseError()
        return jsonify({"status": "success", "resp": resp_json})


api.add_resource(PushResource, '/push')
api.add_resource(CheckoutResource, '/checkout')
