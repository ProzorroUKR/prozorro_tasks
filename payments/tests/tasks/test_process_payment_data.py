import unittest

from unittest.mock import patch, ANY

from payments.message_ids import PAYMENTS_INVALID_PATTERN
from payments.tasks import process_payment_data


class TestHandlerCase(unittest.TestCase):

    @patch("payments.tasks.process_payment_complaint_search")
    def test_handle_valid_description(self, process_payment_complaint_search):
        payment_data = {"description": "UA-2020-03-17-000090-a.a2-12AD3F12"}

        process_payment_data(payment_data)

        process_payment_complaint_search.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment_data,
                payment_params={
                    "complaint": "UA-2020-03-17-000090-a.a2",
                    "code": "12AD3F12"
                },
            )
        )


    @patch("payments.logging.push_payment_message")
    @patch("payments.tasks.process_payment_complaint_search")
    def test_handle_invalid_description(self, process_payment_complaint_search, push_payment_message):
        payment_data = {"description": "Invalid"}

        process_payment_data(payment_data)

        push_payment_message.assert_called_once_with(
            payment_data, PAYMENTS_INVALID_PATTERN, ANY
        )

        process_payment_complaint_search.apply_async.assert_not_called()
