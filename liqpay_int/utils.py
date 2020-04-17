import json
from urllib.parse import urljoin

import liqpay
import requests

from environment_settings import (
    LIQPAY_PUBLIC_KEY,
    LIQPAY_PRIVATE_KEY,
    LIQPAY_SANDBOX_PUBLIC_KEY,
    LIQPAY_SANDBOX_PRIVATE_KEY,
    LIQPAY_TAX_PERCENTAGE,
    LIQPAY_API_HOST,
    LIQPAY_API_PROXIES,
)

class LiqPay(liqpay.LiqPay):
    def __init__(self, public_key, private_key, host=LIQPAY_API_HOST, proxies=LIQPAY_API_PROXIES):
        super(LiqPay, self).__init__(public_key=public_key, private_key=private_key, host=host)
        self._proxies = proxies

    def api(self, url, params=None):
        params = self._prepare_params(params)

        json_encoded_params = json.dumps(params)
        private_key = self._private_key
        signature = self._make_signature(private_key, json_encoded_params, private_key)

        request_url = urljoin(self._host, url)
        request_data = {'data': json_encoded_params, 'signature': signature}
        response = requests.post(request_url, data=request_data, verify=False, proxies=self._proxies)
        return json.loads(response.content)


def get_liqpay_keys(sandbox=False):
    if sandbox:
        return LIQPAY_SANDBOX_PUBLIC_KEY, LIQPAY_SANDBOX_PRIVATE_KEY
    return LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY


def generate_liqpay_params(data, sandbox=False):
    public_key, private_key = get_liqpay_keys(sandbox=sandbox)
    params = {"version": 3, "public_key": public_key}
    params.update(data)
    return params


def generate_liqpay_checkout_params(data, payment_params, complaint_data, sandbox=False):
    amount = float(complaint_data.get("value").get("amount"))
    if LIQPAY_TAX_PERCENTAGE:
        amount /= (1.0 - (LIQPAY_TAX_PERCENTAGE / 100.0))
    params = {
        "action": "payment_prepare",
        "action_payment": "pay",
        "order_id": "{}-{}".format(
            payment_params.get("complaint"),
            payment_params.get("code").upper()
        ),
        "amount": amount,
        "currency": complaint_data.get("value").get("currency")
    }
    params.update(data)
    return generate_liqpay_params(params, sandbox=sandbox)


def generate_liqpay_receipt_params(data, sandbox=False):
    params = {"action": "ticket"}
    params.update(data)
    return generate_liqpay_params(params, sandbox=sandbox)


def liqpay_request(data=None, sandbox=False):
    public_key, private_key = get_liqpay_keys(sandbox=sandbox)
    liqpay = LiqPay(public_key, private_key)
    return liqpay.api("/api/request", data)


def liqpay_decode(data=None, sandbox=False):
    public_key, private_key = get_liqpay_keys(sandbox=sandbox)
    liqpay = LiqPay(public_key, private_key)
    return liqpay.decode_data_from_str(data)


def liqpay_sign(data=None, sandbox=False):
    public_key, private_key = get_liqpay_keys(sandbox=sandbox)
    liqpay = LiqPay(public_key, private_key)
    return liqpay._make_signature(private_key, data, private_key)
