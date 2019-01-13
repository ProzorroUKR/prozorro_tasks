
VERSION = "2.0.0"
DOC_TYPE = 'registerExtract'
IDENTIFICATION_SCHEME = 'UA-EDR'
DOC_AUTHOR = "IdentificationBot"
FILE_NAME = 'edr_identification.yaml'
pre_qualification_procedures = (
    'aboveThresholdEU',
    'competitiveDialogueUA',
    'competitiveDialogueEU',
    'esco',
)
qualification_procedures = (
    'aboveThresholdUA',
    'aboveThresholdUA.defense',
    'aboveThresholdEU',
    'competitiveDialogueUA.stage2',
    'competitiveDialogueEU.stage2',
    'esco',
)
ID_PASSPORT_LEN = 9

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
DEFAULT_RETRY_AFTER = 5

MONGODB_SERVER_SELECTION_TIMEOUT = 5
MONGODB_CONNECT_TIMEOUT = 5
MONGODB_SOCKET_TIMEOUT = 5
