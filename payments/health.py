import json
import time
from datetime import datetime, timedelta

import kombu

from contextlib import contextmanager

from celery_worker.celery import app
from celery_worker.locks import get_mongodb_client
from environment_settings import (
    PUBLIC_API_HOST,
    API_HOST,
    MONGODB_SERVER_SELECTION_TIMEOUT,
    MONGODB_CONNECT_TIMEOUT,
    MONGODB_SOCKET_TIMEOUT,
    CELERY_BROKER_URL,
)
from liqpay_int.utils import generate_liqpay_status_params, liqpay_request
from payments.results_db import get_statuses_list, save_status
from payments.utils import request_head, request_complaint_search
from tasks_utils.settings import CONNECT_TIMEOUT, READ_TIMEOUT


HEATH_DATA_INTERVAL_SECONDS = 10 * 60


def response_health_status(response):
    if response and response.status_code in [200, 201]:
        return "available"
    return "unavailable"


def liqpay_health_status(response):
    if response and response.status_code == 200:
        try:
            json_data = json.loads(response.text)
            code = json_data["code"]
        except Exception:
            return "invalid"
        if code == "payment_not_found":
            return "available"
        else:
            return code
    return "unavailable"


def response_status_code(response):
    return getattr(response, "status_code", None)


def response_header(response, name):
    if response and hasattr(response, "headers"):
        return response.headers.get(name)
    return None


def mongodb_info():
    client = get_mongodb_client()
    return client.server_info()


def request_search():
    return request_complaint_search("health")


def request_public():
    return request_head(host=PUBLIC_API_HOST, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))


def request_lb():
    return request_head(host=API_HOST, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))


def request_liqpay():
    params = generate_liqpay_status_params({"order_id": ""})
    return liqpay_request(params, sandbox=False, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))


@contextmanager
def try_method(method):
    try:
        response = method()
    except Exception as exc:
        response = None
        exception = type(exc).__name__
    else:
        exception = None
    yield response, exception


def api_health(request_method):
    start = time.time()
    with try_method(request_method) as (response, exception):
        total_seconds = time.time() - start
        health_item = {
            "status": response_health_status(response),
            "connect_timeout": CONNECT_TIMEOUT,
            "read_timeout": READ_TIMEOUT,
            "total_seconds": total_seconds,
        }
        if response:
            health_item.update({
                "url": getattr(response, "url", None),
                "status_code": response_status_code(response),
                "request_id": response_header(response, "X-Request-ID"),
                "client_request_id": response_header(response, "X-Client-Request-ID"),
            })
        if exception:
            health_item.update({
                "exception": str(exception)
            })
        return health_item


def liqpay_health(request_method):
    start = time.time()
    with try_method(request_method) as (response, exception):
        total_seconds = time.time() - start
        health_item = {
            "status": liqpay_health_status(response),
            "connect_timeout": CONNECT_TIMEOUT,
            "read_timeout": READ_TIMEOUT,
            "total_seconds": total_seconds,
        }
        if response:
            health_item.update({
                "url": getattr(response, "url", None),
                "status_code": response_status_code(response),
            })
        if exception:
            health_item.update({
                "exception": str(exception)
            })
        return health_item


def mongodb_health():
    start = time.time()
    with try_method(mongodb_info) as (info, exception):
        total_seconds = time.time() - start
        health_item = {
            "status": "available" if info else "unavailable",
            "server_selection_timeout": MONGODB_SERVER_SELECTION_TIMEOUT,
            "connect_timeout": MONGODB_CONNECT_TIMEOUT,
            "socket_timeout": MONGODB_SOCKET_TIMEOUT,
            "total_seconds": total_seconds
        }
        if exception:
            health_item.update({
                "exception": str(exception)
            })
        return health_item

def rabbitmq_report():
    con_opts = {
        "max_retries": 2,
        "interval_start": 1,
        "interval_step": 1,
        "interval_max": 2,
    }
    connection = kombu.Connection(CELERY_BROKER_URL, connect_timeout=5, transport_options=con_opts)
    inspect = app.control.inspect(timeout=1, connection=connection)
    return inspect.report()


def rabbitmq_health():
    start = time.time()
    with try_method(rabbitmq_report) as (info, exception):
        total_seconds = time.time() - start
        health_item = {
            "status": "available" if info else "unavailable",
            "total_seconds": total_seconds
        }
        if exception:
            health_item.update({"exception": str(exception)})
        return health_item


def health():
    health_data = {
        "cdb_public": api_health(request_public),
        "cdb_lb": api_health(request_lb),
        "cdb_search": api_health(request_search),
        "liqpay": liqpay_health(request_liqpay),
        "mongodb": mongodb_health(),
        "rabbitmq": rabbitmq_health(),
    }
    health_statuses = [health_item["status"] for health_item in health_data.values()]
    health_overall = "available" if all([
        status == "available" for status in health_statuses
    ]) else "unavailable"
    return dict(status=health_overall, **health_data)


def save_health_data(data):
    historical = list(get_statuses_list(limit=1))
    if len(historical):
        historical_last = historical[0]
        delta = datetime.now() - historical_last["createdAt"]
        status_changed = False
        for key in historical_last["data"].keys():
            if key != "status":
                prev_status = historical_last["data"].get(key, {}).get("status")
                curr_status = data.get(key, {}).get("status")
                if prev_status != curr_status:
                    status_changed = True
        if delta > timedelta(seconds=HEATH_DATA_INTERVAL_SECONDS) or status_changed:
            return save_status(data)
    else:
        return save_status(data)


def get_health_data():
    return list(get_statuses_list())
