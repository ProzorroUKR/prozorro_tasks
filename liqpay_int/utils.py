from liqpay import LiqPay

from environment_settings import (
    LIQPAY_PUBLIC_KEY,
    LIQPAY_PRIVATE_KEY,
    LIQPAY_SANDBOX_PUBLIC_KEY,
    LIQPAY_SANDBOX_PRIVATE_KEY,
)


def generate_liqpay_params(args):
    params = {
        "version": 3,
        "public_key": LIQPAY_PUBLIC_KEY,
    }
    params.update(args)
    return params


def generate_liqpay_checkout_params(args):
    params = {
        "action": "payment_prepare",
        "action_payment": "pay",
    }
    params.update(args)
    return generate_liqpay_params(params)


def generate_liqpay_receipt_params(args):
    params = {
        "action": "ticket",
    }
    params.update(args)
    return generate_liqpay_params(params)

def liqpay_request(params=None, sandbox=False):
    if sandbox:
        public_key, private_key = LIQPAY_SANDBOX_PUBLIC_KEY, LIQPAY_SANDBOX_PRIVATE_KEY
    else:
        public_key, private_key = LIQPAY_PUBLIC_KEY, LIQPAY_PRIVATE_KEY
    liqpay = LiqPay(public_key, private_key)
    return liqpay.api("/api/request", params)
