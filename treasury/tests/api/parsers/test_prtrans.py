from app.tests.base import BaseTestCase
from unittest.mock import patch
from treasury.tests.helpers import prepare_request


class PrtransTestCase(BaseTestCase):
    @patch("treasury.api.methods.prtrans.save_transaction")
    def test_required_fields(self, save_transaction_mock):
        xml = b"""<?xml version="1.0" encoding="windows-1251"?>
    <root method_name="PRTrans">
      <record>
        <ref>1</ref>
        <doc_sq>18.44</doc_sq>
        <doc_datd>2020-03-11T00:00:00+02:00</doc_datd>
        <doc_nam_a>Test</doc_nam_a>
        <doc_iban_a>UA678201720355110002000080850</doc_iban_a>
        <doc_nam_b>Test</doc_nam_b>
        <doc_iban_b>UA098201720355179002000014715</doc_iban_b>
        <msrprd_date>2020-03-11T00:00:00+02:00</msrprd_date>
        <id_contract>11C2E7D03AF649668BF9FFB1D0EF767D</id_contract>
      </record>
    </root>"""
        response = self.client.post(
            '/treasury',
            data=prepare_request(xml),
            headers={"Content-Type": "application/xml"}
        )
        self.assertEqual(
            response.data,
            b"<xml><Body><Response>"
            b"<ResultCode>30</ResultCode>"
            b"<ResultMessage>'doc_status' is required</ResultMessage>"
            b"</Response></Body></xml>"
        )
        self.assertEqual(response.status_code, 400)
        save_transaction_mock.assert_not_called()
