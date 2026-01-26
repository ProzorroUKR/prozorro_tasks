from chronograph.handlers import chronograph_handler
from edr_bot.handlers import edr_bot_tender_handler
from environment_settings import SYNC_PAYMENTS_RESOLUTIONS, SYNC_AUTOCLIENT_PAYMENTS_RESOLUTIONS
from fiscal_bot.handlers import fiscal_bot_tender_handler
from nazk_bot.handlers import nazk_bot_tender_handler
from payments.handlers import payments_tender_handler
from autoclient_payments.handlers import autoclient_payments_tender_handler
from treasury.handlers import contract_handler

TENDER_HANDLERS = [
    edr_bot_tender_handler,
    fiscal_bot_tender_handler,
    nazk_bot_tender_handler,
]
if SYNC_PAYMENTS_RESOLUTIONS:
    TENDER_HANDLERS.append(payments_tender_handler)
if SYNC_AUTOCLIENT_PAYMENTS_RESOLUTIONS:
    TENDER_HANDLERS.append(autoclient_payments_tender_handler)

CONTRACT_HANDLERS = [
    contract_handler,
]

FRAMEWORK_HANDLERS = [
    chronograph_handler("framework"),
]

AGREEMENT_HANDLERS = [
    chronograph_handler("agreement"),
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

AGREEMENT_OPT_FIELDS = [
    'status',
    'agreementID',
    'agreementType',
    'next_check',
    'dateModified',
]
