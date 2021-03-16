from environment_settings import FISCAL_API_HOST, TIMEZONE, FISCAL_API_PROXIES, CONNECT_TIMEOUT, READ_TIMEOUT
from fiscal_bot.tasks import check_for_response_file
from fiscal_bot.settings import REQUEST_MAX_RETRIES, WORKING_TIME
from celery.exceptions import Retry
from datetime import datetime
from unittest.mock import patch, Mock, call
import requests
import unittest


@patch("fiscal_bot.tasks.WORKING_TIME", {"start": (9, 0), "end": (21, 0)})
class CheckResponseTestCase(unittest.TestCase):
    fail_response = {
        'message': None,
        'status': 'OK',
        'id': None,
        'kvt1Base64': None,
        'kvt1Fname': None,
        'kvtList': [
            {
                'kvtBase64': '',
                'kvtFname': '26591010101017J1499101100000000311220182659.KVT',
                'numKvt': 1,
                'finalKvt': 0,
                'status': 1
            }
        ]
    }

    response = {
        'message': None,
        'status': 'OK',
        'id': None,
        'kvt1Base64': None,
        'kvt1Fname': None,
        'kvtList': [
            {
                'kvtBase64': '',
                'kvtFname': '26591010101017J1499101100000000311220182659.KVT',
                'numKvt': 1,
                'finalKvt': 0,
                'status': 1
            },
            {
                'kvtBase64': 'aGVsbG8=',
                'kvtFname': '26591010101017J1499101100000000311220182659_FINAL.KVT',
                'numKvt': 1,
                'finalKvt': 1,
                'status': 1
            }
        ]
    }

    @patch("fiscal_bot.tasks.get_working_datetime")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    def test_check_request_fail_request(
            self, save_check_receipt_task_info_mock, get_check_receipt_tasks_by_tender_id_mock,
            get_check_receipt_task_info_by_id_mock, requests_mock,
            decode_and_save_data_mock, retry_mock, get_wt_mock
    ):
        get_wt_mock.return_value = datetime(2007, 1, 2, 13, 30)
        retry_mock.side_effect = Retry
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        _tender_id = "f" * 32
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": _tender_id,
            "award_id": "c" * 32,
        }
        request_time = TIMEZONE.localize(datetime(2019, 3, 29, 15, 47))
        requests_mock.post.side_effect = requests.exceptions.ConnectionError()

        with patch("fiscal_bot.tasks.working_days_count_since") as working_days_count_since_mock:
            working_days_count_since_mock.return_value = 0
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=request_time,
                    requests_reties=0
                )
        working_days_count_since_mock.assert_called_once_with(
            request_time, working_weekends_enabled=True
        )
        retry_mock.assert_called_once_with(exc=requests_mock.post.side_effect)
        save_check_receipt_task_info_mock.assert_called_once_with(
            _tender_id, None
        )

        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
            headers={'User-agent': 'prozorro_tasks'},
        )
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.get_working_datetime")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    def test_check_request_fail_status(
            self, save_check_receipt_task_info_mock, get_check_receipt_tasks_by_tender_id_mock,
            get_check_receipt_task_info_by_id_mock, requests_mock,
            decode_and_save_data_mock, retry_mock, get_wt_mock, task_request_mock
    ):
        task_mock_id = task_request_mock.id = "k" * 32
        task_request_mock.retries = 0
        get_wt_mock.return_value = datetime(2007, 1, 2, 13, 30)
        retry_mock.side_effect = Retry
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        _tender_id = "f" * 32,
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": _tender_id,
            "award_id": "c" * 32,
        }

        requests_mock.post.return_value = Mock(
            status_code=502,
            text="Bad Gateway",
            headers={"Retry-After": 10}
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=0
                )

        retry_mock.assert_called_once_with(
            countdown=10
        )
        save_check_receipt_task_info_mock.assert_called_once_with(
            _tender_id, task_mock_id
        )
        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
            headers={'User-agent': 'prozorro_tasks'},
        )
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.get_now")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    def test_check_request_fail_no_report(
            self, save_check_receipt_task_info_mock, get_check_receipt_tasks_by_tender_id_mock,
            get_check_receipt_task_info_by_id_mock, prepare_receipt_request_mock, requests_mock,
            decode_and_save_data_mock, retry_mock, get_now_mock, task_request_mock
    ):
        task_mock_id = task_request_mock.id = "k" * 32
        task_request_mock.retries = 0

        get_now_mock.return_value = TIMEZONE.localize(datetime(2007, 1, 2, 20, 30))
        retry_mock.side_effect = Retry
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        _tender_id = "f" * 32
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": _tender_id,
            "award_id": "c" * 32,
        }

        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.fail_response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):

            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=0
                )

        retry_mock.assert_called_once_with(
            eta=TIMEZONE.localize(datetime(2007, 1, 3, 9))
        )
        save_check_receipt_task_info_mock.assert_called_once_with(
            _tender_id, task_mock_id
        )
        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
            headers={'User-agent': 'prozorro_tasks'},
        )
        prepare_receipt_request_mock.delay.assert_not_called()
        decode_and_save_data_mock.delay.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    def test_check_request_success(
            self, get_check_receipt_tasks_by_tender_id_mock, get_check_receipt_task_info_by_id_mock,
            prepare_receipt_request_mock, requests_mock, save_check_receipt_task_info_mock, decode_and_save_data_mock,
            task_request_mock
    ):
        task_mock_id = task_request_mock.id = "k" * 32
        task_request_mock.retries = 0

        request_data = "aGVsbG8="
        _tender_id = "f" * 32
        supplier = {
            "tender_id": _tender_id,
            "award_id": "c" * 32,
        }
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 0):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=0
            )

        save_check_receipt_task_info_mock.assert_has_calls(
            [
                call(_tender_id, task_mock_id),
                call(
                    _tender_id, task_mock_id, has_called_new_check_receipt_task=False,
                    receipt_file_successfully_saved=True
                )
            ]

        )
        self.assertEqual(
            requests_mock.post.call_args_list,
            [
                call(
                    '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
                    data=request_data,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    proxies=FISCAL_API_PROXIES,
                    headers={'User-agent': 'prozorro_tasks'},
                )
            ]
        )

        self.assertEqual(
            decode_and_save_data_mock.delay.call_args_list,
            [
                call(
                    self.response["kvtList"][-1]["kvtFname"],
                    self.response["kvtList"][-1]["kvtBase64"],
                    supplier["tender_id"],
                    supplier["award_id"],
                )
            ]
        )
        prepare_receipt_request_mock.delay.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.get_now")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    def test_check_on_3rd_wd_1st_request_retry(
            self, get_check_receipt_tasks_by_tender_id_mock, get_check_receipt_task_info_by_id_mock,
            save_check_receipt_task_info_mock, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock,
            retry_mock, get_now_mock, task_request_mock
    ):
        task_mock_id = task_request_mock.id = "k" * 32
        get_now_mock.return_value = TIMEZONE.localize(datetime(2020, 1, 2, 20, 30))
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None
        save_check_receipt_task_info_mock.return_value = None

        retry_mock.side_effect = Retry
        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.fail_response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=0
                )

        save_check_receipt_task_info_mock.assert_called_once_with(
            supplier["tender_id"],
            task_mock_id,
            has_called_new_check_receipt_task=True
        )
        prepare_receipt_request_mock.delay.assert_called_once_with(
            supplier=supplier,
            requests_reties=1
        )

        retry_mock.assert_called_once_with(
            eta=TIMEZONE.localize(datetime(2020, 1, 3, 9))
        )

        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
            headers={'User-agent': 'prozorro_tasks'},
        )
        decode_and_save_data_mock.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    def test_check_on_3rd_wd_2nd_request_retry_and_than_success_check_for_1st(
            self, get_check_receipt_tasks_by_tender_id_mock, get_check_receipt_task_info_by_id_mock,
            save_check_receipt_task_info_mock, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock,
            task_request_mock
    ):
        task_request_mock.retries = 20
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }

        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                requests_reties=1
            )

        prepare_receipt_request_mock.delay.assert_called_once_with(
            supplier=supplier,
            requests_reties=2
        )
        self.assertEqual(save_check_receipt_task_info_mock.call_count, 2)

        self.assertEqual(
            requests_mock.post.call_args_list,
            [
                call(
                    '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
                    data=request_data,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    proxies=FISCAL_API_PROXIES,
                    headers={'User-agent': 'prozorro_tasks'},
                )
            ]
        )

        self.assertEqual(
            decode_and_save_data_mock.delay.call_args_list,
            [
                call(
                    self.response["kvtList"][-1]["kvtFname"],
                    self.response["kvtList"][-1]["kvtBase64"],
                    supplier["tender_id"],
                    supplier["award_id"],
                )
            ]
        )

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.get_now")
    @patch("fiscal_bot.tasks.check_for_response_file.retry")
    @patch("fiscal_bot.tasks.decode_and_save_data")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    def test_check_on_3rd_wd_3rd_request_retry(
            self, get_check_receipt_tasks_by_tender_id_mock, get_check_receipt_task_info_by_id_mock,
            save_check_receipt_task_info_mock, requests_mock, prepare_receipt_request_mock, decode_and_save_data_mock,
            retry_mock, get_now_mock, task_request_mock

    ):
        task_request_mock.retries = 20
        get_now_mock.return_value = TIMEZONE.localize(datetime(2020, 1, 2, 20, 30))
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = None

        retry_mock.side_effect = Retry
        requests_mock.post.return_value = Mock(
            status_code=200,
            json=lambda: self.fail_response,
        )

        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 3):
            with self.assertRaises(Retry):
                check_for_response_file(
                    request_data=request_data,
                    supplier=supplier,
                    request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
                    requests_reties=REQUEST_MAX_RETRIES
                )

        prepare_receipt_request_mock.delay.assert_not_called()

        retry_mock.assert_called_once_with(
            eta=TIMEZONE.localize(datetime(2020, 1, 3, 9))
        )

        requests_mock.post.assert_called_once_with(
            '{}/cabinet/public/api/exchange/kvt_by_id'.format(FISCAL_API_HOST),
            data=request_data,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            proxies=FISCAL_API_PROXIES,
            headers={'User-agent': 'prozorro_tasks'},
        )
        decode_and_save_data_mock.assert_not_called()
        save_check_receipt_task_info_mock.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.working_days_count_since")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    def test_check_another_successful_task_for_tender_existed(
            self, save_check_receipt_task_info_mock, get_check_receipt_tasks_by_tender_id_mock,
            get_check_receipt_task_info_by_id_mock, working_days_mock, task_request_mock
    ):
        task_request_mock.retries = 10
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        get_check_receipt_tasks_by_tender_id_mock.return_value = [
            {
                "tenderId": "f" * 32,
                "checkForResponseFileTaskId": "1"*10,
                "hasCalledNewCheckReceiptTask": True,
                "receiptFileSuccessfullySaved": False,
            },
            {
                "tenderId": "f" * 32,
                "checkForResponseFileTaskId": "2" * 10,
                "hasCalledNewCheckReceiptTask": False,
                "receiptFileSuccessfullySaved": True,  # <--
            }
        ]

        check_for_response_file(
            request_data=request_data,
            supplier=supplier,
            request_time=TIMEZONE.localize(datetime(2019, 3, 29, 15, 47)),
            requests_reties=REQUEST_MAX_RETRIES
        )

        save_check_receipt_task_info_mock.assert_not_called()
        working_days_mock.assert_not_called()
        get_check_receipt_task_info_by_id_mock.assert_not_called()

    @patch("celery.app.task.Task.request")
    @patch("fiscal_bot.tasks.requests")
    @patch("fiscal_bot.tasks.save_check_receipt_task_info")
    @patch("fiscal_bot.tasks.prepare_receipt_request")
    @patch("fiscal_bot.tasks.get_check_receipt_task_info_by_id")
    @patch("fiscal_bot.tasks.get_check_receipt_tasks_info_by_tender_id")
    def test_current_check_task_has_called_new_check_receipt_task_and_working_days_for_check_passed(
            self, get_check_receipt_tasks_by_tender_id_mock, get_check_receipt_task_info_by_id_mock,
            prepare_receipt_request_mock, save_check_receipt_task_info_mock, requests_mock, task_request_mock
    ):
        task_request_mock.retries = 10
        request_data = "aGVsbG8="
        supplier = {
            "tender_id": "f" * 32,
            "award_id": "c" * 32,
        }
        get_check_receipt_tasks_by_tender_id_mock.return_value = []
        get_check_receipt_task_info_by_id_mock.return_value = {
            "tenderId": "f" * 32,
            "checkForResponseFileTaskId": "f2e0e0d6-3dc3-4b52-9ee1-4729574ed3c2",
            "hasCalledNewCheckReceiptTask": True,
            "receiptFileSuccessfullySaved": False
        }

        # need <= 10 working days for requests_reties == 0
        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 12):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2020, 3, 29, 15, 47)),
                requests_reties=0
            )
        prepare_receipt_request_mock.assert_not_called()
        requests_mock.post.assert_not_called()
        save_check_receipt_task_info_mock.assert_not_called()

        # need <= 8 working days for requests_reties == 1
        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 9):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2020, 3, 29, 15, 47)),
                requests_reties=1
            )
        prepare_receipt_request_mock.assert_not_called()
        requests_mock.post.assert_not_called()
        save_check_receipt_task_info_mock.assert_not_called()

        # need <= 6 working days for requests_reties == 2
        with patch("fiscal_bot.tasks.working_days_count_since", lambda *_, **k: 7):
            check_for_response_file(
                request_data=request_data,
                supplier=supplier,
                request_time=TIMEZONE.localize(datetime(2020, 3, 29, 15, 47)),
                requests_reties=2
            )
        prepare_receipt_request_mock.assert_not_called()
        requests_mock.post.assert_not_called()
        save_check_receipt_task_info_mock.assert_not_called()
