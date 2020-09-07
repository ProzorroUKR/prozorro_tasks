import unittest
import requests

from unittest.mock import patch, Mock, call, ANY

from celery.exceptions import Retry

from tasks_utils.settings import DEFAULT_RETRY_AFTER
from liqpay_int.tasks import process_payment_complaint_patch
from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_EXCEPTION,
    PAYMENTS_PATCH_COMPLAINT_CODE_ERROR,
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
)


class TestHandlerCase(unittest.TestCase):

    def test_handle_connection_error(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        patch_data = {"patch_test_field": "patch_test_value"}

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.side_effect = requests.exceptions.ConnectionError()

            process_payment_complaint_patch.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_payment_complaint_patch(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    patch_data=patch_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_EXCEPTION, ANY),
                ]
            )

        process_payment_complaint_patch.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER,
            exc=requests_mock.patch.side_effect
        )

    def test_handle_429_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {"patch_test_field": "patch_test_value"}

        process_payment_complaint_patch.retry = Mock(
            side_effect=Retry
        )

        ret_aft = 13

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=429,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={"Retry-After": ret_aft}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_patch(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    patch_data=patch_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_patch.retry.assert_called_once_with(
            countdown=ret_aft
        )

    def test_handle_412_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {"patch_test_field": "patch_test_value"}

        process_payment_complaint_patch.retry = Mock(
            side_effect=Retry
        )

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=412,
                cookies=Mock(get_dict=Mock(return_value=cookies))
            )

            with self.assertRaises(Retry):
                process_payment_complaint_patch(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    patch_data=patch_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_patch.retry.assert_called_once_with(
            countdown=0,
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data=patch_data,
                cookies=cookies,
            )
        )

    def test_handle_500_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {"patch_test_field": "patch_test_value"}

        process_payment_complaint_patch.retry = Mock(
            side_effect=Retry
        )

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=500,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_patch(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    patch_data=patch_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_patch.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER
        )

    def test_handle_404_response(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {"patch_test_field": "patch_test_value"}

        process_payment_complaint_patch.retry = Mock(
            side_effect=Retry
        )

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=404,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_patch(
                    complaint_params=complaint_params,
                    payment_data=payment_data,
                    patch_data=patch_data,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_patch.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER
        )

    @patch("payments.tasks.process_payment_complaint_recheck")
    def test_handle_403_response(self, process_payment_complaint_recheck):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {"patch_test_field": "patch_test_value"}

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=403,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                headers={}
            )

            process_payment_complaint_patch(
                complaint_params=complaint_params,
                payment_data=payment_data,
                patch_data=patch_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_CODE_ERROR, ANY),
                ]
            )

        process_payment_complaint_recheck.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment_data,
                complaint_params=complaint_params,
                patch_data=patch_data,
                cookies=cookies
            )
        )

    def test_handle_200_response_complaint_pending(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {
            "status": "pending"
        }

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies))
            )

            requests_mock.patch.return_value.json.return_value = {"data": {"author": "test"}}

            process_payment_complaint_patch(
                complaint_params=complaint_params,
                payment_data=payment_data,
                patch_data=patch_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS, ANY),
                ]
            )

    def test_handle_200_response_complaint_mistaken(self):
        payment_data = {"description": "test"}
        complaint_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}
        patch_data = {
            "status": "mistaken"
        }

        with patch("payments.utils.requests") as requests_mock, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            requests_mock.patch.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies))
            )

            requests_mock.patch.return_value.json.return_value = {"data": {"author": "test"}}

            process_payment_complaint_patch(
                complaint_params=complaint_params,
                payment_data=payment_data,
                patch_data=patch_data,
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS, ANY),
                ]
            )
