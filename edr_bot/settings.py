VERSION = "2.0.0"
DOC_TYPES = {
    "1.0": "registerExtract",
    "2.0": "registerUSR",
}
IDENTIFICATION_SCHEME = 'UA-EDR'
DOC_AUTHOR = "IdentificationBot"
FILE_NAME = 'edr_identification.yaml'
pre_qualification_procedures = (
    'aboveThresholdEU',
    'competitiveDialogueUA',
    'competitiveDialogueEU',
    'esco',
    'closeFrameworkAgreementUA',
)
qualification_procedures = (
    'aboveThreshold',
    'aboveThresholdUA',
    'aboveThresholdUA.defense',
    'aboveThresholdEU',
    'competitiveDialogueUA.stage2',
    'competitiveDialogueEU.stage2',
    'esco',
    'closeFrameworkAgreementUA',
    'simple.defense',
)
qualification_procedures_limited = (
    'reporting',
)
ID_PASSPORT_LEN = 9

EDR_REGISTRATION_STATUSES = {
    -1: 'cancelled',
    1: 'registered',
    2: 'beingTerminated',
    3: 'terminated',
    4: 'banckruptcyFiled',
    5: 'banckruptcyReorganization',
    6: 'invalidRegistraton',
}

EDR_IDENTIFICATION_SCHEMA = "UA-EDR"
EDR_ACTIVITY_KIND_SCHEME = "КВЕД"
