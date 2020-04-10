import requests

from celery.utils.log import get_task_logger

from celery_worker.celery import app
from liqpay_int.utils import liqpay_request
from tasks_utils.requests import get_exponential_request_retry_countdown

logger = get_task_logger(__name__)

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True, max_retries=20)
def process_liqpay_request(self, params, sandbox=False):
    try:
        resp_json = liqpay_request(data=params, sandbox=sandbox)
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.error("Liqpay api request failed.")
        countdown = get_exponential_request_retry_countdown(self)
        raise self.retry(countdown=countdown, exc=exc)
    else:
        return resp_json
