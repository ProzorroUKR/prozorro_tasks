from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request
from treasury.api.methods.method_factory import MethodFactory
from treasury.api.methods.prtrans import PRTrans


class MethodFactoryTestCase(BaseTestCase):
    @patch("treasury.api.methods.prtrans.save_transaction")
    def test_invalid_method(self, save_transaction_mock):
        response = self.client.post(
            '/treasury',
            data=prepare_request(b"", method_name="eee"),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b'<xml><Body><Response>'
            b'<ResultCode>40</ResultCode>'
            b'<ResultMessage>Invalid method: eee</ResultMessage>'
            b'</Response></Body></xml>'
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.assert_not_called()

    def test_create_method(self):

        result = MethodFactory.create('PRTrans')
        self.assertEqual(result, PRTrans)
