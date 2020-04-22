import logging

from pymongo.errors import PyMongoError

from tasks_utils.requests import get_exponential_request_retry_countdown
from payments.results_db import push_payment_message


class PaymentResultsLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        extra = {}
        super(PaymentResultsLoggerAdapter, self).__init__(logger, extra)

    def log(self, level, msg, *args, **kwargs):
        extra = kwargs.setdefault("extra", self.extra)
        task = kwargs.pop("task", None)
        payment_data = kwargs.pop("payment_data", None)
        message_id = extra.get("MESSAGE_ID", None)
        if payment_data and message_id:
            try:
                push_payment_message(payment_data, message_id, msg)
            except PyMongoError as exc:
                if task:
                    countdown = get_exponential_request_retry_countdown(task)
                    raise task.retry(countdown=countdown, exc=exc)
                raise
        super(PaymentResultsLoggerAdapter, self).log(level, msg, *args, **kwargs)
