from flask_restplus import reqparse, inputs

from liqpay_int.broker.messages import (
    HELP_CHECKOUT_AMOUNT,
    HELP_CHECKOUT_CURR,
    HELP_CHECKOUT_DESC,
    HELP_CHECKOUT_LANG,
    HELP_CHECKOUT_RESULT_URL,
    HELP_CHECKOUT_SERVER_URL,
    HELP_CHECKOUT_ORDER_ID,
    HELP_CHECKOUT_SANDBOX,
    HELP_TICKET_EMAIL,
    HELP_TICKET_ORDER_ID,
    HELP_TICKET_LANG,
    HELP_TICKET_STAMP,
)
from liqpay_int.reqparse import Argument


parser_checkout = reqparse.RequestParser(argument_class=Argument)
parser_checkout.add_argument("amount", location="json", required=True, help=HELP_CHECKOUT_AMOUNT)
parser_checkout.add_argument("currency", location="json", required=True, help=HELP_CHECKOUT_CURR)
parser_checkout.add_argument("description", location="json", required=True, help=HELP_CHECKOUT_DESC)
parser_checkout.add_argument("language", location="json", help=HELP_CHECKOUT_LANG)
parser_checkout.add_argument("result_url", location="json", help=HELP_CHECKOUT_RESULT_URL)
parser_checkout.add_argument("server_url", location="json", help=HELP_CHECKOUT_SERVER_URL)
parser_checkout.add_argument("order_id", location="json", help=HELP_CHECKOUT_ORDER_ID)
parser_checkout.add_argument("sandbox", location="args", help=HELP_CHECKOUT_SANDBOX)

parser_ticket = reqparse.RequestParser(argument_class=Argument)
parser_ticket.add_argument("email", location="json", required=True, help=HELP_TICKET_EMAIL)
parser_ticket.add_argument("order_id", location="json", required=True, help=HELP_TICKET_ORDER_ID)
parser_ticket.add_argument("language", location="json", help=HELP_TICKET_LANG)
parser_ticket.add_argument("stamp", location="json", type=inputs.boolean, help=HELP_TICKET_STAMP)
