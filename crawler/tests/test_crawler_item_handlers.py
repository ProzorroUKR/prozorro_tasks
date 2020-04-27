from unittest.mock import patch, Mock, call
from fiscal_bot.handlers import fiscal_bot_tender_handler
from edr_bot.handlers import edr_bot_tender_handler
import environment_settings
import crawler.tasks
import unittest
import importlib
import os


@patch('celery_worker.locks.get_mongodb_collection', Mock(return_value=Mock(find_one=Mock(return_value=None))))
class CrawlerIHandlersTestCase(unittest.TestCase):

    @patch("crawler.tasks.process_feed.apply_async")
    @patch("crawler.tasks.requests")
    def test_call_item_handlers(self, requests_mock, _):

        requests_mock.utils.cookiejar_from_dict = lambda d: d
        requests_mock.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'data': [
                    {"id": "a" * 32},
                    {"id": "b" * 32},
                ],
                'next_page': {'offset': 2}
            }),
            cookies={}
        )

        item_handlers = [
            Mock(),
            Mock(),
        ]

        with patch("crawler.tasks.TENDER_HANDLERS", item_handlers):
            crawler.tasks.process_feed(offset=1)

        for handler in item_handlers:
            self.assertEqual(
                handler.call_args_list,
                [call({'id': 'a' * 32}),
                 call({'id': 'b' * 32})]
            )

    @patch("fiscal_bot.handlers.fiscal_bot_tender_handler")
    @patch("edr_bot.handlers.edr_bot_tender_handler")
    def test_call_item_filtered_handlers(self, edr_bot_handler_mock, fiscal_bot_handler_mock):
        edr_bot_handler_mock.__name__ = edr_bot_tender_handler.__name__
        fiscal_bot_handler_mock.__name__ = fiscal_bot_tender_handler.__name__

        prev_val = os.environ.get("CRAWLER_TENDER_HANDLERS")
        try:

            os.environ["CRAWLER_TENDER_HANDLERS"] = "edr_bot_tender_handler , whatever,"
            importlib.reload(environment_settings)
            importlib.reload(crawler.tasks)

            with patch("crawler.tasks.requests") as requests_mock:
                with patch("crawler.tasks.process_feed.apply_async"):
                    requests_mock.utils.cookiejar_from_dict = lambda d: d
                    requests_mock.get.return_value = Mock(
                        status_code=200,
                        json=Mock(return_value={
                            'data': [
                                {"id": "a" * 32},
                                {"id": "b" * 32},
                            ],
                            'next_page': {'offset': 2}
                        }),
                        cookies={}
                    )
                    crawler.tasks.process_feed(offset=1)

            fiscal_bot_handler_mock.assert_not_called()
            self.assertEqual(
                edr_bot_handler_mock.call_args_list,
                [call({'id': 'a' * 32}),
                 call({'id': 'b' * 32})]
            )

        finally:
            if prev_val:
                os.environ["CRAWLER_TENDER_HANDLERS"] = prev_val

