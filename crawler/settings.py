from chronograph.handlers import chronograph_framework_handler
from edr_bot.handlers import edr_bot_tender_handler
from fiscal_bot.handlers import fiscal_bot_tender_handler
from payments.handlers import payments_tender_handler
from treasury.handlers import contract_handler

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
DEFAULT_RETRY_AFTER = 5
API_LIMIT = 100
FEED_URL_TEMPLATE = "{host}/api/{version}/{resource}"
WAIT_MORE_RESULTS_COUNTDOWN = 60

TENDER_HANDLERS = [
    edr_bot_tender_handler,
    fiscal_bot_tender_handler,
    payments_tender_handler,
]

CONTRACT_HANDLERS = [
    contract_handler,
]

FRAMEWORK_HANDLERS = [
    chronograph_framework_handler,
]

TENDER_OPT_FIELDS = [
    'auctionPeriod',
    'status',
    'tenderID',
    'lots',
    'procurementMethodType',
    'next_check',
    'dateModified',
]

CONTRACT_OPT_FIELDS = [
    'status',
    'contractID',
    'dateModified',
]

FRAMEWORK_OPT_FIELDS = [
    'status',
    'frameworkID',
    'frameworkType',
    'next_check',
    'dateModified',
]
