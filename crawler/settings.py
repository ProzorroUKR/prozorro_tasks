from chronograph.handlers import chronograph_handler
from edr_bot.handlers import edr_bot_tender_handler
from fiscal_bot.handlers import fiscal_bot_tender_handler
from payments.handlers import payments_tender_handler
from treasury.handlers import contract_handler

TENDER_HANDLERS = [
    edr_bot_tender_handler,
    fiscal_bot_tender_handler,
    payments_tender_handler,
]

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
