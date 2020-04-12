import logging

from pymongo.errors import PyMongoError

from payments.results_db import push_payment_message
from tasks_utils.requests import get_exponential_request_retry_countdown


class PaymentResultsLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super(PaymentResultsLoggerAdapter, self).__init__(logger, None)

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", self.extra or {})
        message_id = extra.get("MESSAGE_ID", "")
        task = kwargs.pop("task", None)
        if "payment_data" in kwargs:
            try:
                push_payment_message(kwargs.pop("payment_data"), message_id, msg)
            except PyMongoError as exc:
                if task:
                    countdown = get_exponential_request_retry_countdown(task)
                    raise task.retry(countdown=countdown, exc=exc)
        return msg, kwargs
