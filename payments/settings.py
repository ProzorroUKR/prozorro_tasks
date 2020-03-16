import os
import re

TENDER_RE = re.compile("(?:/\s*tenders\s*/\s*(?P<tender_id>[0-9a-f]{32})\s*)")
COMPLAINT_RE = re.compile("(?:/\s*complaints\s*/\s*(?P<complaint_id>[0-9a-f]{32})\s*)")
QUALIFICATION_RE = re.compile("(?:/\s*qualifications\s*/\s*(?P<qualification_id>[0-9a-f]{32})\s*)")
AWARD_RE = re.compile("(?:/\s*awards\s*/\s*(?P<award_id>[0-9a-f]{32})\s*)")
CANCELLATION_RE = re.compile("(?:/\s*cancellations\s*/\s*(?P<cancellation_id>[0-9a-f]{32})\s*)")

TENDER_COMPLAINT_TYPE = "tender"
QUALIFICATION_COMPLAINT_TYPE = "qualification"
AWARD_COMPLAINT_TYPE = "award"
CANCELLATION_COMPLAINT_TYPE = "cancellation"

TENDER_COMPLAINT_RE = re.compile(
    "{TENDER_PATH_PATTERN}{COMPLAINT_PATTERN}".format(
        TENDER_PATH_PATTERN=TENDER_RE.pattern,
        COMPLAINT_PATTERN=COMPLAINT_RE.pattern,
    )
)

QUALIFICATION_COMPLAINT_RE = re.compile(
    "{TENDER_PATH_PATTERN}{QUALIFICATION_PATTERN}{COMPLAINT_PATTERN}".format(
        TENDER_PATH_PATTERN=TENDER_RE.pattern,
        QUALIFICATION_PATTERN=QUALIFICATION_RE.pattern,
        COMPLAINT_PATTERN=COMPLAINT_RE.pattern,
    )
)

AWARD_COMPLAINT_RE = re.compile(
    "{TENDER_PATH_PATTERN}{AWARD_PATTERN}{COMPLAINT_PATTERN}".format(
        TENDER_PATH_PATTERN=TENDER_RE.pattern,
        AWARD_PATTERN=AWARD_RE.pattern,
        COMPLAINT_PATTERN=COMPLAINT_RE.pattern,
    )
)

CANCELLATION_COMPLAINT_RE = re.compile(
    "{TENDER_PATH_PATTERN}{CANCELLATION_PATTERN}{COMPLAINT_PATTERN}".format(
        TENDER_PATH_PATTERN=TENDER_RE.pattern,
        CANCELLATION_PATTERN=CANCELLATION_RE.pattern,
        COMPLAINT_PATTERN=COMPLAINT_RE.pattern,
    )
)

COMPLAINT_RE_DICT = {
    TENDER_COMPLAINT_TYPE: TENDER_COMPLAINT_RE,
    QUALIFICATION_COMPLAINT_TYPE: QUALIFICATION_COMPLAINT_RE,
    AWARD_COMPLAINT_TYPE: AWARD_COMPLAINT_RE,
    CANCELLATION_COMPLAINT_TYPE: CANCELLATION_COMPLAINT_RE,
}

ALLOWED_COMPLAINT_PAYMENT_STATUSES = ["draft"]
