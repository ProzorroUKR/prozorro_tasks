from liqpay_int.settings import LIQPAY_PUBLIC_KEY
from celery_worker.celery import app as celery_app


def process_payment(args):
    celery_app.send_task('payments.process_payment', kwargs=dict(payment_data=args))

def generate_checkout_params(args):
    params = {
        "version": 3,
        "public_key": LIQPAY_PUBLIC_KEY,
        "action": "payment_prepare",
        "action_payment": "pay",
        "amount": args.get("amount"),
        "currency": args.get("currency"),
        "description": args.get("description"),
    }
    if args.get("language"):
        params.update({"language": args.get("language")})
    if args.get("result_url"):
        params.update({"result_url": args.get("result_url")})
    return params
