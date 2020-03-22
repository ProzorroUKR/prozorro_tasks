from flask_restplus import reqparse

from liqpay_int.provider.messages import (
    HELP_PUSH_TYPE,
    HELP_PUSH_DATE_OPER,
    HELP_PUSH_AMOUNT,
    HELP_PUSH_CURR,
    HELP_PUSH_ACC,
    HELP_PUSH_OKPO,
    HELP_PUSH_MFO,
    HELP_PUSH_NAME,
    HELP_PUSH_DESC,
)
from liqpay_int.reqparse import Argument


parser_push = reqparse.RequestParser(argument_class=Argument)
parser_push.add_argument('type', location="json", help=HELP_PUSH_TYPE)
parser_push.add_argument('date_oper', location="json", help=HELP_PUSH_DATE_OPER)
parser_push.add_argument('amount', location="json", required=True, help=HELP_PUSH_AMOUNT)
parser_push.add_argument('currency', location="json", required=True, help=HELP_PUSH_CURR)
parser_push.add_argument('account', location="json", help=HELP_PUSH_ACC)
parser_push.add_argument('okpo', location="json", help=HELP_PUSH_OKPO)
parser_push.add_argument('mfo', location="json", help=HELP_PUSH_MFO)
parser_push.add_argument('name', location="json", help=HELP_PUSH_NAME)
parser_push.add_argument('description', location="json", required=True, help=HELP_PUSH_DESC)
