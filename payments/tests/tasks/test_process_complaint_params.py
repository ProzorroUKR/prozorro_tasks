import unittest
import pymongo.errors

from uuid import uuid4
from unittest.mock import patch, Mock
from celery.exceptions import Retry

from tasks_utils.settings import DEFAULT_RETRY_AFTER
from payments.tasks import process_complaint_params
from payments.message_ids import (
    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS,
)


class TestHandlerCase(unittest.TestCase):

    def test_handle_mongodb_error(self):
        complaint_params = {'test_param': 'test_value'}
        complaint_data = {"id": uuid4().hex}

        process_complaint_params.retry = Mock(side_effect=Retry)

        with patch("payments.results_db.get_mongodb_collection") as get_collection:
            collection = Mock()
            get_collection.return_value = collection
            collection.find_one.side_effect = pymongo.errors.PyMongoError()

            with self.assertRaises(Retry):
                process_complaint_params(
                    complaint_params=complaint_params,
                    complaint_data=complaint_data
                )

        process_complaint_params.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER,
            exc=collection.find_one.side_effect
        )

    @patch("payments.tasks.process_complaint_resolution")
    def test_handle_payment(self, process_complaint_resolution):
        complaint_params = {'test_param': 'test_value'}
        complaint_data = {"id": uuid4().hex}

        payment = {"payment": {"description": "Test description"}}

        with patch("payments.tasks.get_payment_item_by_params") as get_payment_item_by_params:
            get_payment_item_by_params.return_value = payment

            process_complaint_params(
                complaint_params=complaint_params,
                complaint_data=complaint_data
            )

            get_payment_item_by_params.assert_called_once_with(
                complaint_params, [
                    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
                    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
                ]
            )

        process_complaint_resolution.apply_async.assert_called_once_with(
            kwargs=dict(
                payment_data=payment.get("payment"),
                complaint_data=complaint_data
            )
        )

    @patch("payments.tasks.process_complaint_resolution")
    def test_handle_payment_resolution_already_exists(self, process_complaint_resolution):
        complaint_params = {'test_param': 'test_value'}
        complaint_data = {"id": uuid4().hex}

        payment = {"payment": {
            "description": "Test description"},
            "resolution": {
                "test_res_field": "test_res_value"
            }}

        with patch("payments.tasks.get_payment_item_by_params") as get_payment_item_by_params:
            get_payment_item_by_params.return_value = payment

            process_complaint_params(
                complaint_params=complaint_params,
                complaint_data=complaint_data
            )

            get_payment_item_by_params.assert_called_once_with(
                complaint_params, [
                    PAYMENTS_PATCH_COMPLAINT_PENDING_SUCCESS,
                    PAYMENTS_PATCH_COMPLAINT_NOT_PENDING_SUCCESS
                ]
            )

        process_complaint_resolution.apply_async.assert_not_called()
