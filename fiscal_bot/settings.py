import os

DOC_TYPE = 'registerFiscal'
IDENTIFICATION_SCHEME = 'UA-EDR'
procedures = (
    'aboveThresholdUA', 'aboveThresholdUA.defense', 'aboveThresholdEU',
    'competitiveDialogueUA.stage2', 'competitiveDialogueEU.stage2',
    'esco',
    'closeFrameworkAgreementUA',
    'simple.defense',
)

WORKING_DAYS_BEFORE_REQUEST_AGAIN = 2
REQUEST_MAX_RETRIES = 2

NUMBER_OF_WORKING_DAYS_FOR_REQUEST_RETRY_MAPPING = {
    0: 10,
    1: 8,
    2: 6
}
assert len(NUMBER_OF_WORKING_DAYS_FOR_REQUEST_RETRY_MAPPING.keys())-1 == REQUEST_MAX_RETRIES

FISCAL_BOT_START_DATE = os.environ.get("FISCAL_BOT_START_DATE", "2019-07-01")
REQUEST_DOC_VERSION = int(os.environ.get("FISCAL_BOT_REQUEST_DOC_VERSION", 2))

WORKING_TIME = {"start": (9, 0), "end": (21, 0)}
