import os

DOC_TYPE = 'registerFiscal'
IDENTIFICATION_SCHEME = 'UA-EDR'
procedures = (
    'aboveThresholdUA', 'aboveThresholdUA.defense', 'aboveThresholdEU',
    'competitiveDialogueUA.stage2', 'competitiveDialogueEU.stage2',
    'esco',
    'closeFrameworkAgreementUA',
)

WORKING_DAYS_BEFORE_REQUEST_AGAIN = 2
REQUEST_MAX_RETRIES = 2
CUSTOM_WORK_DAY = dict(
    start=(9, 0),
    end=(16, 0),
)

FISCAL_BOT_START_DATE = os.environ.get("FISCAL_BOT_START_DATE", "2019-07-01")


