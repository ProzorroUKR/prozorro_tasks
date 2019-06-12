from edr_bot.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from environment_settings import API_TOKEN, API_VERSION, API_HOST
from edr_bot.tasks import attach_doc_to_tender
from unittest.mock import patch, Mock
from celery.exceptions import Retry
import unittest
import requests


class AttachDocTestCase(unittest.TestCase):

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_head_connection_error(self, get_upload_results):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.head.side_effect = requests.exceptions.ConnectionError()

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(file_data=file_data, data=data, tender_id=tender_id,
                                     item_name=item_name, item_id=item_id)

        attach_doc_to_tender.retry.assert_called_once_with(exc=requests_mock.head.side_effect)
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_post_connection_error(self, get_upload_results):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.side_effect = requests.exceptions.ConnectionError()

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(file_data=file_data, data=data, tender_id=tender_id,
                                     item_name=item_name, item_id=item_id)

        attach_doc_to_tender.retry.assert_called_once_with(exc=requests_mock.post.side_effect)
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.set_upload_results_attached")
    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_head_429_response(self, get_upload_results, set_upload_results_attached):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        server_id = "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.head.return_value = Mock(
                status_code=429,
                cookies={'SERVER_ID': server_id}
            )
            requests_mock.post.return_value = Mock(status_code=201)
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(file_data=file_data, data=data,
                                 tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.post.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                host=API_HOST,
                version=API_VERSION,
                item_name=item_name,
                item_id=item_id,
                tender_id=tender_id,
            ),
            json={'data': file_data['data']},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': file_data['meta']['id'],
            },
            cookies={'SERVER_ID': server_id},
        )
        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)
        set_upload_results_attached.assert_called_once_with(data, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_post_429_response(self, get_upload_results):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        ret_aft, server_id = 13, "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=429,
                headers={'Retry-After': ret_aft},
            )
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})

            attach_doc_to_tender.retry = Mock(side_effect=Retry)
            with self.assertRaises(Retry):
                attach_doc_to_tender(file_data=file_data, data=data,
                                     tender_id=tender_id, item_name=item_name, item_id=item_id)

        attach_doc_to_tender.retry.assert_called_once_with(countdown=13.0)
        requests_mock.post.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                host=API_HOST,
                version=API_VERSION,
                item_name=item_name,
                item_id=item_id,
                tender_id=tender_id,
            ),
            json={'data': file_data['data']},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': file_data['meta']['id'],
            },
            cookies={'SERVER_ID': server_id},
        )
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_post_422_response(self, get_upload_results):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        ret_aft, server_id = 13, "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(
                status_code=422,
                text='{"errors": {"url": ["Document url expired."]}}'
            )
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            with patch("edr_bot.tasks.logger") as logger_mock:
                attach_doc_to_tender(file_data=file_data, data=data,
                                     tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.post.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                host=API_HOST,
                version=API_VERSION,
                item_name=item_name,
                item_id=item_id,
                tender_id=tender_id,
            ),
            json={'data': file_data['data']},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': file_data['meta']['id'],
            },
            cookies={'SERVER_ID': server_id},
        )
        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)
        logger_mock.error.assert_called_once_with(
            'Incorrect document data while attaching doc 1 to tender ffffffffffffffffffffffffffffffff: '
            '{"errors": {"url": ["Document url expired."]}}',
            extra={'MESSAGE_ID': 'EDR_ATTACH_DATA_ERROR'}
        )

    @patch("edr_bot.tasks.set_upload_results_attached")
    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_success_post(self, get_upload_results, set_upload_results_attached):
        get_upload_results.return_value = None
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {'meta': 1, 'data': 2}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        server_id = "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(status_code=201)
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(file_data=file_data, data=data,
                                 tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.post.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                host=API_HOST,
                version=API_VERSION,
                item_name=item_name,
                item_id=item_id,
                tender_id=tender_id,
            ),
            json={'data': file_data['data']},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': file_data['meta']['id'],
            },
            cookies={'SERVER_ID': server_id},
        )

        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, {'data': 2}, tender_id, item_name, item_id)
        set_upload_results_attached.assert_called_once_with({'data': 2}, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.set_upload_results_attached")
    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_success_file_data_from_db(self, get_upload_results, set_upload_results_attached):

        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        get_upload_results.return_value = {"file_data": file_data}

        server_id = "e" * 32
        with patch("edr_bot.tasks.requests") as requests_mock:
            requests_mock.post.return_value = Mock(status_code=201)
            requests_mock.head.return_value = Mock(cookies={'SERVER_ID': server_id})
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(file_data=None, data=data,
                                 tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.post.assert_called_once_with(
            "{host}/api/{version}/tenders/{tender_id}/{item_name}s/{item_id}/documents".format(
                host=API_HOST,
                version=API_VERSION,
                item_name=item_name,
                item_id=item_id,
                tender_id=tender_id,
            ),
            json={'data': file_data['data']},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers={
                'Authorization': 'Bearer {}'.format(API_TOKEN),
                'X-Client-Request-ID': file_data['meta']['id'],
            },
            cookies={'SERVER_ID': server_id},
        )

        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)
        set_upload_results_attached.assert_called_once_with(data, tender_id, item_name, item_id)

    @patch("edr_bot.tasks.set_upload_results_attached")
    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_success_without_file_data(self, get_upload_results, set_upload_results_attached):
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        get_upload_results.return_value = None

        with patch("edr_bot.tasks.requests") as requests_mock:
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            with self.assertRaises(AssertionError) as e:
                attach_doc_to_tender(file_data=None, data=data,
                                     tender_id=tender_id, item_name=item_name, item_id=item_id)

            self.assertEqual(
                str(e.exception),
                "Saved results are missed for {} {} {}".format(tender_id, item_name, item_id)
            )

        requests_mock.head.assert_not_called()
        requests_mock.post.assert_not_called()
        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)
        set_upload_results_attached.assert_not_called()

    @patch("edr_bot.tasks.set_upload_results_attached")
    @patch("edr_bot.tasks.get_upload_results")
    def test_handle_success_results_already_attached(self, get_upload_results, set_upload_results_attached):
        file_data, data = {"meta": {"id": 1}, "data": {'test': 3}}, {}
        tender_id, item_name, item_id = "f" * 32, "award", "a" * 32

        get_upload_results.return_value = {"file_data": file_data, "attached": True}

        with patch("edr_bot.tasks.requests") as requests_mock:
            attach_doc_to_tender.retry = Mock(side_effect=Retry)

            attach_doc_to_tender(file_data=None, data=data,
                                 tender_id=tender_id, item_name=item_name, item_id=item_id)

        requests_mock.head.assert_not_called()
        requests_mock.post.assert_not_called()
        attach_doc_to_tender.retry.assert_not_called()
        get_upload_results.assert_called_once_with(attach_doc_to_tender, data, tender_id, item_name, item_id)
        set_upload_results_attached.assert_not_called()

