import logging

from payments.results_db import message_payment_item


class PaymentResultsLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super(PaymentResultsLoggerAdapter, self).__init__(logger, None)

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", self.extra or {})
        message_id = extra.get("MESSAGE_ID")
        payment_data = kwargs.pop("payment_data")
        if payment_data and message_id:
            message_payment_item(payment_data, message_id, msg)
        return msg, kwargs
