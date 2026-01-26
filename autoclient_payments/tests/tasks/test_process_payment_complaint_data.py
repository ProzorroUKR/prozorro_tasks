import unittest
import requests

from unittest.mock import patch, Mock, call, ANY

from celery.exceptions import Retry

from environment_settings import DEFAULT_RETRY_AFTER
from autoclient_payments.data import STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_MISTAKEN
from autoclient_payments.message_ids import (
    PAYMENTS_GET_COMPLAINT_CODE_ERROR,
    PAYMENTS_VALID_PAYMENT,
    PAYMENTS_INVALID_COMPLAINT_VALUE,
    PAYMENTS_INVALID_STATUS,
    PAYMENTS_INVALID_AMOUNT,
    PAYMENTS_INVALID_CURRENCY,
    PAYMENTS_GET_COMPLAINT_SUCCESS,
    PAYMENTS_GET_COMPLAINT_EXCEPTION,
)
from autoclient_payments.tasks import process_payment_complaint_data


class TestHandlerCase(unittest.TestCase):
    def test_handle_connection_error(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
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
                    call(payment_data, PAYMENTS_GET_COMPLAINT_EXCEPTION, ANY),
                ],
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER, exc=requests_mock.get.side_effect
        )

    def test_handle_429_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(side_effect=Retry)

        ret_aft = 13

        with patch("autoclient_payments.utils.requests") as requests_mock, \
            patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=429, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={"Retry-After": ret_aft}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_data.retry.assert_called_once_with(countdown=ret_aft)

    def test_handle_412_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=412,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_data.retry.assert_called_once_with(
            countdown=0,
            kwargs=dict(
                complaint_params=complaint_params,
                payment_data=payment_data,
                cookies=cookies,
            ),
        )

    def test_handle_500_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=500, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_data.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    def test_handle_404_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_data.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=404, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_data(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_data.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    @patch("autoclient_payments.tasks.AUTOCLIENT_PAYMENT_COMPLAINT_PROCESSING_ENABLED", True)
    @patch("autoclient_payments.tasks.process_payment_complaint_patch")
    def test_handle_200_response_valid_complaint(self, process_payment_complaint_patch):
        payment_data = {"description": "test", "amount": "2000", "currency": "UAH"}
        complaint_params = {"tender_id": "test_tender_id", "complaint_id": "test_complaint_id"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": {
                            "id": "test_complaint_id",
                            "status": "draft",
                            "value": {"amount": 2000.0, "currency": "UAH"},
                        },
                    }
                ),
            )

            process_payment_complaint_data(
                complaint_params=complaint_params,
                payment_data=payment_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_VALID_PAYMENT, ANY),
                ],
            )

        process_payment_complaint_patch.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data={"status": STATUS_COMPLAINT_PENDING},
                cookies=cookies,
            )
        )

    @patch("autoclient_payments.tasks.AUTOCLIENT_PAYMENT_COMPLAINT_PROCESSING_ENABLED", True)
    @patch("autoclient_payments.tasks.process_payment_complaint_patch")
    def test_handle_200_response_invalid_complaint_status(self, process_payment_complaint_patch):
        payment_data = {"description": "test", "amount": "2000", "currency": "UAH"}
        complaint_params = {"tender_id": "test_tender_id", "complaint_id": "test_complaint_id"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": {
                            "id": "test_complaint_id",
                            "status": "pending",
                            "value": {"amount": 2000.0, "currency": "UAH"},
                        },
                    }
                ),
            )

            process_payment_complaint_data(
                complaint_params=complaint_params,
                payment_data=payment_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_INVALID_STATUS, ANY),
                ],
            )

        process_payment_complaint_patch.apply_async.assert_not_called()

    @patch("autoclient_payments.tasks.AUTOCLIENT_PAYMENT_COMPLAINT_PROCESSING_ENABLED", True)
    @patch("autoclient_payments.tasks.process_payment_complaint_patch")
    def test_handle_200_response_no_complaint_value(self, process_payment_complaint_patch):
        payment_data = {"description": "test", "amount": "2000", "currency": "UAH"}
        complaint_params = {"tender_id": "test_tender_id", "complaint_id": "test_complaint_id"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": {"id": "test_complaint_id", "status": "draft"},
                    }
                ),
            )

            process_payment_complaint_data(
                complaint_params=complaint_params,
                payment_data=payment_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_INVALID_COMPLAINT_VALUE, ANY),
                ],
            )

        process_payment_complaint_patch.apply_async.assert_not_called()

    @patch("autoclient_payments.tasks.AUTOCLIENT_PAYMENT_COMPLAINT_PROCESSING_ENABLED", True)
    @patch("autoclient_payments.tasks.process_payment_complaint_patch")
    def test_handle_200_response_invalid_value_amount(self, process_payment_complaint_patch):
        payment_data = {"description": "test", "amount": "1", "currency": "UAH"}
        complaint_params = {"tender_id": "test_tender_id", "complaint_id": "test_complaint_id"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": {
                            "id": "test_complaint_id",
                            "status": "draft",
                            "value": {"amount": 2000.0, "currency": "UAH"},
                        },
                    }
                ),
            )

            process_payment_complaint_data(
                complaint_params=complaint_params,
                payment_data=payment_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_INVALID_AMOUNT, ANY),
                ],
            )

        process_payment_complaint_patch.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
                cookies=cookies,
            )
        )

    @patch("autoclient_payments.tasks.AUTOCLIENT_PAYMENT_COMPLAINT_PROCESSING_ENABLED", True)
    @patch("autoclient_payments.tasks.process_payment_complaint_patch")
    def test_handle_200_response_invalid_value_currency(self, process_payment_complaint_patch):
        payment_data = {"description": "test", "amount": "2000", "currency": "USD"}
        complaint_params = {"tender_id": "test_tender_id", "complaint_id": "test_complaint_id"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": {
                            "id": "test_complaint_id",
                            "status": "draft",
                            "value": {"amount": 2000.0, "currency": "UAH"},
                        },
                    }
                ),
            )

            process_payment_complaint_data(
                complaint_params=complaint_params,
                payment_data=payment_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_GET_COMPLAINT_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_INVALID_CURRENCY, ANY),
                ],
            )

        process_payment_complaint_patch.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data={"status": STATUS_COMPLAINT_MISTAKEN},
                cookies=cookies,
            )
        )
