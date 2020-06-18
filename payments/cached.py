from app.app import cache
from payments.utils import request_tender_data, request_complaint_data

CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 5.0
CACHE_TIMEOUT = 60 * 10


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_tender(params):
    try:
        response = request_tender_data(
            tender_id=params.get("tender_id"),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        tender = response.json()["data"]
        return tender
    except Exception as exc:
        pass


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_complaint(params):
    try:
        response = request_complaint_data(
            **params,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        complaint = response.json()["data"]
        return complaint
    except Exception as exc:
        pass
