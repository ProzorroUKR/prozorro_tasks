from app.app import cache
from environment_settings import PUBLIC_API_HOST
from payments.utils import request_cdb_tender_data, request_cdb_complaint_data
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT


CACHE_TIMEOUT = 60 * 10


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_tender(params):
    try:
        response = request_cdb_tender_data(
            tender_id=params.get("tender_id"),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            host=PUBLIC_API_HOST
        )
        tender = response.json()["data"]
        return tender
    except Exception as exc:
        pass


@cache.memoize(timeout=CACHE_TIMEOUT)
def get_complaint(params):
    try:
        response = request_cdb_complaint_data(
            **params,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            host=PUBLIC_API_HOST
        )
        complaint = response.json()["data"]
        return complaint
    except Exception as exc:
        pass
