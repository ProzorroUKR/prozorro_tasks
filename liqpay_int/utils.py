from liqpay import LiqPay

from environment_settings import (
    LIQPAY_PUBLIC_KEY,
    LIQPAY_PRIVATE_KEY,
    LIQPAY_SANDBOX_PUBLIC_KEY,
    LIQPAY_SANDBOX_PRIVATE_KEY,
    LIQPAY_TAX_COEF,
)


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
    params = {
        "action": "payment_prepare",
        "action_payment": "pay",
        "order_id": "{}-{}".format(
            payment_params.get("complaint"),
            payment_params.get("code").upper()
        ),
        "amount": float(complaint_data.get("value").get("amount")) * LIQPAY_TAX_COEF,
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
