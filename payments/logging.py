import logging

from payments.results_db import push_payment_message


class PaymentResultsLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super(PaymentResultsLoggerAdapter, self).__init__(logger, None)

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", self.extra or {})
        message_id = extra.get("MESSAGE_ID")
        payment_data = kwargs.pop("payment_data")
        if payment_data and message_id:
            push_payment_message(payment_data, message_id, msg)
        return msg, kwargs
