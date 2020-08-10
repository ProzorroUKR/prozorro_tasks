import unittest
import pymongo.errors

from uuid import uuid4
from unittest.mock import patch, Mock, call, ANY
from celery.exceptions import Retry

from tasks_utils.settings import DEFAULT_RETRY_AFTER
from payments.tasks import process_complaint_resolution
from payments.message_ids import PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS


class TestHandlerCase(unittest.TestCase):

    def test_handle_mongodb_error(self):
        payment_data = {'test_param': 'test_value'}
        complaint_data = {
            "id": uuid4().hex,
            "status": "mistaken"
        }

        process_complaint_resolution.retry = Mock(side_effect=Retry)

        with patch("payments.results_db.get_mongodb_collection") as get_collection:
            collection = Mock()
            get_collection.return_value = collection
            collection.update_one.side_effect = pymongo.errors.PyMongoError()

            with self.assertRaises(Retry):
                process_complaint_resolution(
                    payment_data=payment_data,
                    complaint_data=complaint_data
                )

        process_complaint_resolution.retry.assert_called_once_with(
            countdown=DEFAULT_RETRY_AFTER,
            exc=collection.update_one.side_effect
        )

    def test_handle_resolution_mistaken(self):
        payment_data = {'test_param': 'test_value'}

        for reject_reason in ["incorrectPayment", "complaintPeriodEnded", "cancelledByComplainant"]:
            complaint_data = {
                "id": uuid4().hex,
                "status": "mistaken",
                "date": "test_date",
                "rejectReason": reject_reason
            }

            resolution = {
                "date": "test_date",
                "type": "mistaken",
                "reason": reject_reason,
                "funds": "complainant",
            }

            with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
                 patch("payments.logging.push_payment_message") as push_payment_message:

                process_complaint_resolution(
                    payment_data=payment_data,
                    complaint_data=complaint_data
                )

                set_payment_resolution.assert_called_once_with(
                    payment_data, resolution
                )

                self.assertEqual(
                    push_payment_message.mock_calls,
                    [
                        call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                    ]
                )

    def test_handle_resolution_mistaken_invalid_reject_reason(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "mistaken",
            "date": "test_date",
            "rejectReason": "someInvalidRejectReason"
        }

        resolution = {
            "date": "test_date",
            "type": "mistaken",
            "reason": "someInvalidRejectReason",
            "funds": None,
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_resolution_satisfied(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "satisfied",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "satisfied",
            "reason": None,
            "funds": "complainant",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_resolution_resolved(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "resolved",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "satisfied",
            "reason": None,
            "funds": "complainant",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

                process_complaint_resolution(
                    payment_data=payment_data,
                    complaint_data=complaint_data
                )

                set_payment_resolution.assert_called_once_with(
                    payment_data, resolution
                )

                self.assertEqual(
                    push_payment_message.mock_calls,
                    [
                        call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                    ]
                )

    def test_handle_resolution_invalid_complainant(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "invalid",
            "rejectReason": "buyerViolationsCorrected",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "invalid",
            "reason": "buyerViolationsCorrected",
            "funds": "complainant",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

                process_complaint_resolution(
                    payment_data=payment_data,
                    complaint_data=complaint_data
                )

                set_payment_resolution.assert_called_once_with(
                    payment_data, resolution
                )

                self.assertEqual(
                    push_payment_message.mock_calls,
                    [
                        call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                    ]
                )

    def test_handle_resolution_invalid_state(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "invalid",
            "rejectReason": "someReason",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "invalid",
            "reason": "someReason",
            "funds": "state",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_resolution_stopped_complainant(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "stopped",
            "rejectReason": "buyerViolationsCorrected",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "stopped",
            "reason": "buyerViolationsCorrected",
            "funds": "complainant",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_resolution_stopped_state(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "stopped",
            "rejectReason": "someReason",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "stopped",
            "reason": "someReason",
            "funds": "state",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_resolution_declined(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "declined",
            "rejectReason": "someReason",
            "dateDecision": "test_date",
        }

        resolution = {
            "date": "test_date",
            "type": "declined",
            "reason": "someReason",
            "funds": "state",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_called_once_with(
                payment_data, resolution
            )

            self.assertEqual(
                push_payment_message.mock_calls,
                [
                    call(payment_data, PAYMENTS_CRAWLER_RESOLUTION_SAVE_SUCCESS, ANY),
                ]
            )

    def test_handle_unexpected_complaint_status(self):
        payment_data = {'test_param': 'test_value'}

        complaint_data = {
            "id": uuid4().hex,
            "status": "draft",
        }

        resolution = {
            "date": "test_date",
            "type": "declined",
            "reason": "someReason",
            "funds": "state",
        }

        with patch("payments.tasks.set_payment_resolution") as set_payment_resolution, \
             patch("payments.logging.push_payment_message") as push_payment_message:

            process_complaint_resolution(
                payment_data=payment_data,
                complaint_data=complaint_data
            )

            set_payment_resolution.assert_not_called()
            push_payment_message.assert_not_called()
