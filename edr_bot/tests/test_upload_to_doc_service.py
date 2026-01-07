from edr_bot.tasks import upload_to_doc_service
from unittest.mock import patch, Mock
from celery.exceptions import Retry
import unittest
import requests


class UploadDocTestCase(unittest.TestCase):

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_connection_error(self, get_upload_results):
        get_upload_results.return_value = None

        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {"content": "test"}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = requests.exceptions.ConnectionError()

            upload_to_doc_service.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id, edr_code="test")

        upload_to_doc_service.retry.assert_called_once_with(exc=requests_mock.post.side_effect)
        get_upload_results.assert_called_once_with(upload_to_doc_service, {"data": {"content": "test"}},
                                                   tender_id, item_name, item_id)

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_429_response(self, get_upload_results):
        get_upload_results.return_value = None

        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {"content": "test"}}, "f" * 32, "award", "a" * 32

        ret_aft = 13
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft}
            )

            upload_to_doc_service.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id, edr_code="test")

        upload_to_doc_service.retry.assert_called_once_with(countdown=ret_aft)
        get_upload_results.assert_called_once_with(upload_to_doc_service, {"data": {"content": "test"}},
                                                   tender_id, item_name, item_id)

    @patch("edr_bot.tasks.save_upload_results")
    @patch("edr_bot.tasks.get_upload_results")
    @patch("edr_bot.tasks.attach_doc_to_tender")
    def test_handle_success(self, attach_doc_to_tender, get_upload_results, save_upload_results):
        get_upload_results.return_value = None
        save_upload_results.return_value = "3" * 24

        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {"content": "test"}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=200,
                json=Mock(return_value={
                    'data': {"test": 1},
                }),
            )

            upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id, edr_code="test")

        file_data = {'data': {"test": 1}, 'meta': {'id': 1}}
        attach_doc_to_tender.delay.assert_called_once_with(
            file_data=file_data,
            data=data,
            tender_id=tender_id,
            item_name=item_name,
            item_id=item_id
        )
        get_upload_results.assert_called_once_with(upload_to_doc_service, {"data": {"content": "test"}},
                                                   tender_id, item_name, item_id)
        save_upload_results.assert_called_once_with(file_data, {"data": {"content": "test"}}, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.save_upload_results")
    @patch("edr_bot.tasks.get_upload_results")
    @patch("edr_bot.tasks.attach_doc_to_tender")
    def test_handle_already_uploaded(self, attach_doc_to_tender, get_upload_results, save_upload_results):
        get_upload_results.return_value = {"Sol": "Tor"}  # Not empty
        save_upload_results.return_value = "3" * 24

        data, tender_id, item_name, item_id = {"meta": {"id": 1}, "data": {"content": "test"}}, "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            upload_to_doc_service(data=data, tender_id=tender_id, item_name=item_name, item_id=item_id, edr_code="test")

        requests_mock.post.assert_not_called()
        attach_doc_to_tender.delay.assert_called_once_with(
            file_data=None,
            data=data,
            tender_id=tender_id,
            item_name=item_name,
            item_id=item_id
        )
        get_upload_results.assert_called_once_with(
            upload_to_doc_service,
            {"data": {"content": "test"}},
            tender_id,
            item_name,
            item_id
        )
        save_upload_results.assert_not_called()
