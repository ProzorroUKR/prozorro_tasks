from environment_settings import LIQPAY_PUBLIC_KEY


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
    if args.get("server_url"):
        params.update({"server_url": args.get("server_url")})
    return params
