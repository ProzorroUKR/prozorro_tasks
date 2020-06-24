from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request


class MainApiTestCase(BaseTestCase):
    @patch("treasury.tasks.process_transaction")
    def test_invalid_password(self, process_transaction_mock):
        response = self.client.post(
            '/treasury',
            data=prepare_request(b"", password="eee"),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>10</ResultCode>'
            b'<ResultMessage>Invalid login or password</ResultMessage></Response>'
            b'</Body></xml>'
        )
        self.assertEqual(response.status_code, 403)
        process_transaction_mock.assert_not_called()
