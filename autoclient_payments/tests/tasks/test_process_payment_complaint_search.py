import unittest
import requests
import pymongo.errors

from unittest.mock import patch, Mock, call, ANY
from hashlib import sha512

from celery.exceptions import Retry

from environment_settings import DEFAULT_RETRY_AFTER
from autoclient_payments.tasks import process_payment_complaint_search
from autoclient_payments.message_ids import (
    PAYMENTS_SEARCH_SUCCESS,
    PAYMENTS_SEARCH_VALID_CODE,
    PAYMENTS_SEARCH_EXCEPTION,
    PAYMENTS_SEARCH_CODE_ERROR,
    PAYMENTS_SEARCH_FAILED,
    PAYMENTS_SEARCH_INVALID_COMPLAINT,
    PAYMENTS_SEARCH_INVALID_CODE,
)


class TestHandlerCase(unittest.TestCase):
    def test_handle_connection_error(self):
        payment_data = {"OSND": "test"}
        payment_params = {"test": "test"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_payment_complaint_search.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_payment_complaint_search(
                    payment_data=payment_data,
                    payment_params=payment_params,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_EXCEPTION, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER, exc=requests_mock.get.side_effect
        )

    @patch("autoclient_payments.tasks.process_payment_complaint_data")
    def test_handle_mongodb_error(self, process_payment_complaint_data):
        complaint_token = "test_token"
        complaint_code = sha512(complaint_token.encode()).hexdigest()[:8].upper()
        payment_data = {"OSND": "UA-2020-03-17-000090-a.a2-{code}".format(code=complaint_code)}
        payment_params = {"complaint": "UA-2020-03-17-000090-a.a2", "code": complaint_code}
        complaint_params = {"tender_id": "test_tender_id"}
        complaint_access = {"token": complaint_token}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.results_db.get_mongodb_collection") as get_collection, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": [{"access": complaint_access, "params": complaint_params}],
                    }
                ),
            )

            collection = Mock()
            get_collection.return_value = collection
            collection.update_one.side_effect = pymongo.errors.PyMongoError()

            with self.assertRaises(Retry):
                process_payment_complaint_search(payment_data, payment_params)

            self.assertEqual(push_payment_message.mock_calls, [])

        process_payment_complaint_search.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER, exc=collection.update_one.side_effect
        )

    def test_handle_429_response(self):
        payment_data = {"OSND": "test"}
        payment_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        ret_aft = 13

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=429, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={"Retry-After": ret_aft}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_search(
                    payment_data=payment_data,
                    payment_params=payment_params,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(countdown=ret_aft)

    def test_handle_412_response(self):
        payment_data = {"OSND": "test"}
        payment_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=412,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
            )

            with self.assertRaises(Retry):
                process_payment_complaint_search(
                    payment_data=payment_data,
                    payment_params=payment_params,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(
            countdown=0,
            kwargs=dict(
                payment_data=payment_data,
                payment_params=payment_params,
                cookies=cookies,
            ),
        )

    def test_handle_500_response(self):
        payment_data = {"OSND": "test"}
        payment_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=500, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_search(
                    payment_data=payment_data,
                    payment_params=payment_params,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    def test_handle_404_response(self):
        payment_data = {"OSND": "test"}
        payment_params = {"test": "test"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=404, cookies=Mock(get_dict=Mock(return_value=cookies)), headers={}
            )

            with self.assertRaises(Retry):
                process_payment_complaint_search(
                    payment_data=payment_data,
                    payment_params=payment_params,
                )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_CODE_ERROR, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    @patch("autoclient_payments.tasks.process_payment_complaint_data")
    def test_handle_200_response_valid_complaint(self, process_payment_complaint_data):
        complaint_token = "test_token"
        complaint_code = sha512(complaint_token.encode()).hexdigest()[:8].upper()
        payment_data = {"OSND": "UA-2020-03-17-000090-a.a2-{code}".format(code=complaint_code)}
        payment_params = {"complaint": "UA-2020-03-17-000090-a.a2", "code": complaint_code}
        complaint_params = {"tender_id": "test_tender_id"}
        complaint_access = {"token": complaint_token}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.set_payment_params") as set_payment_params, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": [{"access": complaint_access, "params": complaint_params}],
                    }
                ),
            )

            process_payment_complaint_search(payment_data, payment_params)

            set_payment_params.assert_called_once_with(payment_data, complaint_params)

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_SEARCH_VALID_CODE, ANY),
                ],
            )

        process_payment_complaint_data.apply_async.assert_called_once_with(
            kwargs=dict(complaint_params=complaint_params, payment_data=payment_data, cookies=cookies)
        )

    @patch("autoclient_payments.tasks.process_payment_complaint_data")
    def test_handle_200_response_invalid_complaint(self, process_payment_complaint_data):
        payment_data = {"OSND": "UA-2020-03-17-000090-a.a2-11111111"}
        payment_params = {"complaint": "UA-2020-03-17-000090-a.a2", "code": "11111111"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        process_payment_complaint_search.retry = Mock(side_effect=Retry)

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.set_payment_params") as set_payment_params, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": [],
                    }
                ),
            )

            with self.assertRaises(Retry):
                process_payment_complaint_search(payment_data, payment_params)

            set_payment_params.assert_not_called()

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_FAILED, ANY),
                ],
            )

        process_payment_complaint_search.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

        process_payment_complaint_data.apply_async.assert_not_called()

    @patch("autoclient_payments.tasks.COMPLAINT_NOT_FOUND_MAX_RETRIES", 0)
    @patch("autoclient_payments.tasks.process_payment_complaint_data")
    def test_handle_200_response_invalid_complaint_max_retries(self, process_payment_complaint_data):
        payment_data = {"OSND": "UA-2020-03-17-000090-a.a2-11111111"}
        payment_params = {"complaint": "UA-2020-03-17-000090-a.a2", "code": "11111111"}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.set_payment_params") as set_payment_params, \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": [],
                    }
                ),
            )

            process_payment_complaint_search(payment_data, payment_params)

            set_payment_params.assert_not_called()

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_FAILED, ANY),
                    call(payment_data, PAYMENTS_SEARCH_INVALID_COMPLAINT, ANY),
                ],
            )

        process_payment_complaint_data.apply_async.assert_not_called()

    @patch("autoclient_payments.tasks.COMPLAINT_NOT_FOUND_MAX_RETRIES", 0)
    @patch("autoclient_payments.tasks.process_payment_complaint_data")
    def test_handle_200_response_invalid_code(self, process_payment_complaint_data):
        complaint_token = "test_token"
        payment_data = {"OSND": "UA-2020-03-17-000090-a.a2-11111111"}
        payment_params = {"complaint": "UA-2020-03-17-000090-a.a2", "code": "11111111"}
        complaint_params = {"tender_id": "test_tender_id"}
        complaint_access = {"token": complaint_token}
        cookies = {"TEST_COOKIE": "TEST_COOKIE_VALUE"}

        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.set_payment_params"), \
             patch("autoclient_payments.logging.push_payment_message") as push_payment_message:
            requests_mock.get.return_value = Mock(
                status_code=200,
                cookies=Mock(get_dict=Mock(return_value=cookies)),
                json=Mock(
                    return_value={
                        "data": [{"access": complaint_access, "params": complaint_params}],
                    }
                ),
            )

            process_payment_complaint_search(payment_data, payment_params)

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_SEARCH_SUCCESS, ANY),
                    call(payment_data, PAYMENTS_SEARCH_INVALID_CODE, ANY),
                ],
            )

        process_payment_complaint_data.apply_async.assert_not_called()
