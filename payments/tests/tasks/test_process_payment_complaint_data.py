import unittest
import requests

from unittest.mock import patch, Mock, call, ANY

from celery.exceptions import Retry

from tasks_utils.settings import DEFAULT_RETRY_AFTER
from payments.message_ids import (
    PAYMENTS_GET_TENDER_EXCEPTION,
    PAYMENTS_GET_TENDER_CODE_ERROR,
)
from payments.tasks import process_payment_complaint_data


class TestHandlerCase(unittest.TestCase):

    def test_handle_connection_error(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_payment_complaint_data.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_TENDER_EXCEPTION, ANY),
                ]
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER,
            exc=requests_mock.get.side_effect
        )

    def test_handle_429_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(
            side_effect=Retry
        )

        ret_aft = 13

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.get.return_value = Mock(
                status_code=429,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={"Retry-After": ret_aft}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_TENDER_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=ret_aft
        )

    def test_handle_500_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(
            side_effect=Retry
        )

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.get.return_value = Mock(
                status_code=500,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_TENDER_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER
        )

    def test_handle_404_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(
            side_effect=Retry
        )

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.get.return_value = Mock(
                status_code=404,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_TENDER_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER
        )

    def test_handle_200_response(self):
        # TODO: test valid data
        pass
