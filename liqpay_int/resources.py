from flask import Blueprint, jsonify
from flask_restplus import Resource, reqparse
from liqpay.liqpay3 import LiqPay

from liqpay_int.api import RestPlusApi
from app.auth import login_group_required, ip_group_required
from environment_settings import (
    LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY, LIQPAY_SANDBOX_PUBLIC_KEY,
    LIQPAY_SANDBOX_PRIVATE_KEY,
)
from liqpay_int.exceptions import LiqpayResponseError, LiqpayResponseFailureError
from liqpay_int.utils import generate_checkout_params
from celery_worker.celery import app as celery_app


API_VERSION = 1
API_PREFIX = "/api/v{}".format(API_VERSION)

bp = Blueprint('payments_resources', __name__)
api = RestPlusApi(bp, prefix=API_PREFIX, doc=API_PREFIX, authorizations={
    'basicAuth': {
        'type': 'basic',
    }
})


class PushResource(Resource):
    parser_push = reqparse.RequestParser()
    parser_push.add_argument('type', location="json", help='Тип операции (debit, credit)')
    parser_push.add_argument('date_oper', location="json", help='Дата операции')
    parser_push.add_argument('amount', location="json", required=True, help='Сумма операции')
    parser_push.add_argument('currency', location="json", required=True, help='Валюта операции')
    parser_push.add_argument('okpo', location="json", help='Номер счета, с которого выполнена операция')
    parser_push.add_argument('mfo', location="json", help='МФО счета, с которого выполнена операция')
    parser_push.add_argument('name', location="json", help='ОКПО счета, с которого выполнена операция')
    parser_push.add_argument(
        'description', location="json", required=True,
        help='Название счета, с которого выполнена операция'
    )

    method_decorators = [ip_group_required("payment_providers")]

    @api.expect(parser_push, validate=True)
    def post(self):
        celery_app.send_task('payments.process_payment', kwargs=dict(payment_data=self.parser_push.parse_args()))
        return jsonify({"status": "success"})


class CheckoutResource(Resource):
    parser_checkout = reqparse.RequestParser()
    parser_checkout.add_argument(
        'amount', location="json", required=True,
        help="Сумма платежа. Например: 2000"
    )
    parser_checkout.add_argument(
        'currency', location="json", required=True,
        help="Валюта платежа. Например: UAH"
    )
    parser_checkout.add_argument(
        'description', location="json", required=True,
        help="Назначение платежа"
    )
    parser_checkout.add_argument(
        'language', location="json",
        help="Язык клиента ru, uk, en"
    )
    parser_checkout.add_argument(
        'result_url', location="json",
        help="URL в Вашем магазине на который покупатель будет переадресован после завершения покупки. "
             "Максимальная длина 510 символов."
    )
    parser_checkout.add_argument(
        'server_url', location="json",
        help="URL API в Вашем магазине для уведомлений об изменении статуса платежа (сервер->сервер). "
             "Максимальная длина 510 символов. Подробнее: https://www.liqpay.ua/documentation/api/callback"
    )
    parser_checkout.add_argument(
        'order_id', location="json",
        help="Уникальный ID покупки в Вашем магазине. Максимальная длина 255 символов."
    )
    parser_checkout.add_argument(
        'sandbox', location="args",
        help="Включить тестовый режим. Подробнее: https://www.liqpay.ua/documentation/api/sandbox"
    )

    method_decorators = [login_group_required("brokers")]

    @api.expect(parser_checkout, validate=True)
    def post(self):
        args = self.parser_checkout.parse_args()
        params = generate_checkout_params(args)
        if args.get("sandbox", False):
            public_key, private_key = LIQPAY_SANDBOX_PUBLIC_KEY, LIQPAY_SANDBOX_PRIVATE_KEY
        else:
            public_key, private_key = LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY
        liqpay = LiqPay(public_key, private_key)
        try:
            resp_json = liqpay.api("/api/request", params)
        except Exception as ex:
            raise LiqpayResponseFailureError()
        else:
            if resp_json.get("result") == "ok":
                return jsonify({
                    "status": "success",
                    "url_checkout": resp_json.get("url_checkout")
                })
            else:
                raise LiqpayResponseError(liqpay_err_description=resp_json.get("err_description"))


api.add_resource(PushResource, '/push')
api.add_resource(CheckoutResource, '/checkout')
