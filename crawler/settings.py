
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
DEFAULT_RETRY_AFTER = 5
API_LIMIT = 100
FEED_URL_TEMPLATE = "{host}/api/{version}/{resource}?feed=changes&descending={descending}" \
                    "&offset={offset}&limit={limit}&opt_fields={opt_fields}"
API_OPT_FIELDS = [
    'auctionPeriod',
    'status',
    'tenderID',
    'lots',
    'procurementMethodType',
    'next_check',
    'dateModified',
]

WAIT_MORE_RESULTS_COUNTDOWN = 60

