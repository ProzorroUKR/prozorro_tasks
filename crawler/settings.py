import os
import pytz

PUBLIC_API_HOST = "http://public.api.openprocurement.org"
API_VERSION = 2.4
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
API_LIMIT = 100
API_OPT_FIELDS = [
    'auctionPeriod',
    'status',
    'tenderID',
    'lots',
    'procurementMethodType',
    'next_check',
    'dateModified',
]
TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Europe/Kiev"))
