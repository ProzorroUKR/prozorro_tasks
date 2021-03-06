from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request


class MainApiTestCase(BaseTestCase):
    @patch("treasury.tasks.process_transaction")
    def test_invalid_password(self, process_transaction_mock):
        response = self.client.post(
            '/treasury',
            data=prepare_request(b"", password="eee"),
            headers={"Content-Type": "application/xml", "User-agent": "prozorro_tasks"}
        )
        self.assertEqual(
            response.data,
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Body><Response>'
            b'<ResultCode>10</ResultCode>'
            b'<ResultMessage>Invalid login or password</ResultMessage></Response>'
            b'</Body>'
        )
        self.assertEqual(response.status_code, 403)
        process_transaction_mock.assert_not_called()
