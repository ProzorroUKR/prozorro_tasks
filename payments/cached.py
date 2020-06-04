from app.app import cache
from payments.utils import request_tender_data, request_complaint_data

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 5.0
CACHE_TIMEOUT = 60 * 10


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_tender(params):
    try:
        response = request_tender_data(tender_id=params.get("tender_id"), timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except Exception as exc:
        pass
    else:
        tender = response.json()["data"]
        return tender


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_complaint(params):
    try:
        response = request_complaint_data(**params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except Exception as exc:
        pass
    else:
        complaint = response.json()["data"]
        return complaint
