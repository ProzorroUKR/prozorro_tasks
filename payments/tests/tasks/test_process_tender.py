import unittest
import requests

from uuid import uuid4
from unittest.mock import patch, Mock, call

from celery.exceptions import Retry

from tasks_utils.settings import DEFAULT_RETRY_AFTER
from payments.tasks import process_tender
from payments.utils import (
    ALLOWED_COMPLAINT_RESOLUTION_STATUSES,
)
from payments.data import STATUS_COMPLAINT_DRAFT, STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_ACCEPTED


class TestHandlerCase(unittest.TestCase):

    def test_handle_connection_error(self):
        tender_id = "f" * 32

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.side_effect = requests.exceptions.ConnectionError()

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(
                countdown=DEFAULT_RETRY_AFTER,
                exc=requests_mock.get.side_effect
            )

    def test_handle_429_response(self):
        tender_id = "f" * 32

        ret_aft = 13
        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=429,
                headers={"Retry-After": ret_aft}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(countdown=ret_aft)

    def test_handle_500_response(self):
        tender_id = "f" * 32

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=500,
                headers={}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    def test_handle_404_response(self):
        tender_id = "f" * 32

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=404,
                headers={}
            )

            process_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                process_tender(tender_id)

            process_tender.retry.assert_called_once_with(countdown=DEFAULT_RETRY_AFTER)

    @patch("payments.tasks.process_complaint_params")
    def test_handle_200_response_tender_complaints(self, process_complaint_params):
        tender_id = uuid4().hex

        allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in ALLOWED_COMPLAINT_RESOLUTION_STATUSES
        ]

        not_allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in [STATUS_COMPLAINT_DRAFT, STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_ACCEPTED] 
        ]

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "data": {
                        "id": tender_id,
                        "complaints": allowed_complaints_data + not_allowed_complaints_data
                    },
                })
            )

            process_tender(tender_id)

        self.assertEqual(
            process_complaint_params.apply_async.call_args_list,
            [
                call(
                    kwargs=dict(
                        complaint_params={
                            "item_id": None,
                            "item_type": None,
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id
                        },
                        complaint_data=complaint_data
                    )
                ) for complaint_data in allowed_complaints_data
            ]
        )


    @patch("payments.tasks.process_complaint_params")
    def test_handle_200_response_qualification_complaints(self, process_complaint_params):
        tender_id = uuid4().hex
        qualification_id = uuid4().hex

        allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in ALLOWED_COMPLAINT_RESOLUTION_STATUSES
        ]

        not_allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in [STATUS_COMPLAINT_DRAFT, STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_ACCEPTED] 
        ]

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "data": {
                        "id": tender_id,
                        "qualifications": [{
                            "id": qualification_id,
                            "complaints": allowed_complaints_data + not_allowed_complaints_data
                        }],
                    },
                })
            )

            process_tender(tender_id)

        self.assertEqual(
            process_complaint_params.apply_async.call_args_list,
            [
                call(
                    kwargs=dict(
                        complaint_params={
                            "item_id": qualification_id,
                            "item_type": "qualifications",
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id
                        },
                        complaint_data=complaint_data
                    )
                ) for complaint_data in allowed_complaints_data
            ]
        )


    @patch("payments.tasks.process_complaint_params")
    def test_handle_200_response_award_complaints(self, process_complaint_params):
        tender_id = uuid4().hex
        award_id = uuid4().hex

        allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in ALLOWED_COMPLAINT_RESOLUTION_STATUSES
        ]

        not_allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in [STATUS_COMPLAINT_DRAFT, STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_ACCEPTED] 
        ]

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "data": {
                        "id": tender_id,
                        "awards": [{
                            "id": award_id,
                            "complaints": allowed_complaints_data + not_allowed_complaints_data
                        }],
                    },
                })
            )

            process_tender(tender_id)

        self.assertEqual(
            process_complaint_params.apply_async.call_args_list,
            [
                call(
                    kwargs=dict(
                        complaint_params={
                            "item_id": award_id,
                            "item_type": "awards",
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id
                        },
                        complaint_data=complaint_data
                    )
                ) for complaint_data in allowed_complaints_data
            ]
        )


    @patch("payments.tasks.process_complaint_params")
    def test_handle_200_response_cancellation_complaints(self, process_complaint_params):
        tender_id = uuid4().hex
        cancellation_id = uuid4().hex

        allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in ALLOWED_COMPLAINT_RESOLUTION_STATUSES
        ]

        not_allowed_complaints_data = [
            {"id": uuid4().hex, "status": status}
            for status in [STATUS_COMPLAINT_DRAFT, STATUS_COMPLAINT_PENDING, STATUS_COMPLAINT_ACCEPTED] 
        ]

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "data": {
                        "id": tender_id,
                        "cancellations": [{
                            "id": cancellation_id,
                            "complaints": allowed_complaints_data + not_allowed_complaints_data
                        }],
                    },
                })
            )

            process_tender(tender_id)

        self.assertEqual(
            process_complaint_params.apply_async.call_args_list,
            [
                call(
                    kwargs=dict(
                        complaint_params={
                            "item_id": cancellation_id,
                            "item_type": "cancellations",
                            "complaint_id": complaint_data["id"],
                            "tender_id": tender_id
                        },
                        complaint_data=complaint_data
                    )
                ) for complaint_data in allowed_complaints_data
            ]
        )

    @patch("payments.tasks.process_complaint_params")
    def test_handle_200_response_no_complaints(self, process_complaint_params):
        tender_id = uuid4().hex

        with patch("payments.utils.requests") as requests_mock:
            requests_mock.get.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    "data": {
                        "id": tender_id,
                    },
                })
            )

            process_tender(tender_id)

        process_complaint_params.apply_async.assert_not_called()
