import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from urllib.parse import urlencode

import pymongo.errors
import requests
from celery.exceptions import Retry

from autoclient_payments.enums import TransactionType
from autoclient_payments.tasks import sync_autoclient_payments
from autoclient_payments.tests.conftest import TRANSACTION_DATA
from autoclient_payments.utils import PB_TRANSACTIONS_URL, PB_HEADERS, PB_QUERY_DATE_FORMAT
from environment_settings import PB_ACCOUNT, PB_AUTOCLIENT_RELEASE_DATE


class TestHandlerCase(unittest.TestCase):
    def test_sync_autoclient_payments(self):
        with patch("autoclient_payments.tasks.get_last_transaction") as get_last_transaction_mock, \
             patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.save_payment_item") as save_payment_item_mock, \
             patch("autoclient_payments.tasks.process_payment_data") as process_payment_data_mock:

            get_last_transaction_mock.return_value = {"dateOper": "2026-01-01T12:00:00+02:00"}
            requests_mock.get.return_value = MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "transactions": [TRANSACTION_DATA],
                        "exist_next_page": False,
                        "next_page_id": None,
                    }
                ),
            )
            sync_autoclient_payments()

            get_last_transaction_mock.assert_called_once()
            query_args = {
                "acc": PB_ACCOUNT,
                "limit": 100,
                "startDate": max(
                    datetime.fromisoformat(PB_AUTOCLIENT_RELEASE_DATE).date(),
                    datetime.fromisoformat(get_last_transaction_mock.return_value["dateOper"]).date() - timedelta(
                        days=1)
                ).strftime(PB_QUERY_DATE_FORMAT),
            }
            requests_mock.get.assert_called_once_with(f"{PB_TRANSACTIONS_URL}?{urlencode(query_args)}", headers=PB_HEADERS)
            save_payment_item_mock.assert_called_once_with(TRANSACTION_DATA, "system")
            process_payment_data_mock.apply_async.assert_called_once_with(kwargs=dict(payment_data=TRANSACTION_DATA))

    def test_sync_autoclient_payments_not_sync_debit(self):
        with patch("autoclient_payments.tasks.get_last_transaction") as get_last_transaction_mock, \
             patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.save_payment_item") as save_payment_item_mock, \
             patch("autoclient_payments.tasks.process_payment_data") as process_payment_data_mock:

            get_last_transaction_mock.return_value = {"dateOper": "2026-01-01T12:00:00+02:00"}
            transaction_data = {**TRANSACTION_DATA, "TRANTYPE": TransactionType.DEBIT}
            requests_mock.get.return_value = MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "transactions": [transaction_data],
                        "exist_next_page": False,
                        "next_page_id": None,
                    }
                ),
            )
            sync_autoclient_payments()

            get_last_transaction_mock.assert_called_once()
            query_args = {
                "acc": PB_ACCOUNT,
                "limit": 100,
                "startDate": max(
                    datetime.fromisoformat(PB_AUTOCLIENT_RELEASE_DATE).date(),
                    datetime.fromisoformat(get_last_transaction_mock.return_value["dateOper"]).date() - timedelta(
                        days=1)
                ).strftime(PB_QUERY_DATE_FORMAT),
            }
            requests_mock.get.assert_called_once_with(f"{PB_TRANSACTIONS_URL}?{urlencode(query_args)}", headers=PB_HEADERS)
            save_payment_item_mock.assert_called_once_with(transaction_data, "system")
            process_payment_data_mock.apply_async.assert_not_called()

    def test_sync_autoclient_payments_pymongo_error(self):
        with patch("autoclient_payments.tasks.get_last_transaction") as get_last_transaction_mock, \
             patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.save_payment_item") as save_payment_item_mock, \
             patch("autoclient_payments.tasks.process_payment_data") as process_payment_data_mock:
            get_last_transaction_mock.return_value = {"dateOper": "2026-01-01T12:00:00+02:00"}
            requests_mock.get.return_value = MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value={
                        "transactions": [TRANSACTION_DATA],
                        "exist_next_page": False,
                        "next_page_id": None,
                    }
                ),
            )
            save_payment_item_mock.side_effect = pymongo.errors.PyMongoError()
            sync_autoclient_payments()

            get_last_transaction_mock.assert_called_once()
            query_args = {
                "acc": PB_ACCOUNT,
                "limit": 100,
                "startDate": max(
                    datetime.fromisoformat(PB_AUTOCLIENT_RELEASE_DATE).date(),
                    datetime.fromisoformat(get_last_transaction_mock.return_value["dateOper"]).date() - timedelta(
                        days=1)
                ).strftime(PB_QUERY_DATE_FORMAT),
            }
            requests_mock.get.assert_called_once_with(f"{PB_TRANSACTIONS_URL}?{urlencode(query_args)}", headers=PB_HEADERS)
            save_payment_item_mock.assert_called_once_with(TRANSACTION_DATA, "system")
            process_payment_data_mock.apply_async.assert_not_called()

    def test_sync_autoclient_payments_PB_request_error(self):
        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.get_last_transaction") as last_transaction_mock:
            last_transaction_mock.return_value = {"dateOper": "2026-01-01T12:00:00+02:00"}
            requests_mock.get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError()
            sync_autoclient_payments.retry = MagicMock(side_effect=Retry)
            with self.assertRaises(Retry):
                sync_autoclient_payments()

    def test_sync_autoclient_payments_PB_connection_error(self):
        with patch("autoclient_payments.utils.requests") as requests_mock, \
             patch("autoclient_payments.tasks.get_last_transaction") as last_transaction_mock:
            last_transaction_mock.return_value = {"dateOper": "2026-01-01T12:00:00+02:00"}
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()
            sync_autoclient_payments.retry = MagicMock(side_effect=Retry)
            with self.assertRaises(Retry):
                sync_autoclient_payments()
