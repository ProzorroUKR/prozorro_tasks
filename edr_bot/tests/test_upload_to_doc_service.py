from edr_bot.tasks import upload_to_doc_service
from unittest.mock import patch, Mock
from celery.exceptions import Retry
import unittest
import requests


class UploadDocTestCase(unittest.TestCase):

    def test_handle_connection_error(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = requests.exceptions.ConnectionError()

            upload_to_doc_service.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            upload_to_doc_service.retry.assert_called_once_with(exc=requests_mock.post.side_effect)

    def test_handle_429_response(self):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}}, "f" * 32, "award", "a" * 32

        ret_aft = 13
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft}
            )

            upload_to_doc_service.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

            upload_to_doc_service.retry.assert_called_once_with(countdown=ret_aft)

    @patch("edr_bot.tasks.attach_doc_to_tender")
    def test_handle_success(self, attach_doc_to_tender):
        data, tender_id, item_name, item_id = {"meta": {"id": 1}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {"test": 1},
                }),
            )

            upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id)

        attach_doc_to_tender.delay.assert_called_once_with(
            data={'data': {"test": 1}, 'meta': {'id': 1}},
            tender_id=tender_id,
            item_name=item_name,
            item_id=item_id
        )
