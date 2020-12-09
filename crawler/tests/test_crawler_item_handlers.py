from unittest.mock import patch, Mock, call

from crawler.resources import ResourceConfigProvider, ResourceConfigBuilder
from crawler.tasks import process_feed
import unittest


@patch('celery_worker.locks.get_mongodb_collection', Mock(return_value=Mock(find_one=Mock(return_value=None))))
class CrawlerIHandlersTestCase(unittest.TestCase):

    @patch("crawler.tasks.process_feed.apply_async", Mock())
    @patch("crawler.tasks.requests")
    def test_call_item_handlers(self, requests_mock):
        cookies = {"some_cookie": "some_test_cookie"}

        requests_mock.get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={
                'data': [
                    {"id": "a" * 32},
                    {"id": "b" * 32},
                ],
                'next_page': {'offset': 2}
            }),
            cookies=Mock(get_dict=Mock(return_value=cookies)),
        )

        item_handlers = [
            Mock(__name__='first_handler'),
            Mock(__name__='second_handler'),
        ]

        disabled_item_handlers = [
            Mock(__name__='third_handler'),
            Mock(__name__='fourth_handler'),
        ]

        class Builder(ResourceConfigBuilder):
            handlers = item_handlers + disabled_item_handlers
            enabled_handlers_names = ["first_handler", "second_handler", "whatever"]
            opt_fields = ("first_field", "second_field")

        configs = ResourceConfigProvider()
        configs.register_builder("tenders", Builder())

        with patch("crawler.tasks.resources.configs", configs):
            process_feed(offset=1)

        for handler in item_handlers:
            self.assertEqual(
                handler.call_args_list,
                [
                    call({'id': 'a' * 32}, cookies=cookies),
                    call({'id': 'b' * 32}, cookies=cookies)
                ]
            )

        for handler in disabled_item_handlers:
            handler.assert_not_called()
