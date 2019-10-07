from datetime import datetime
from fiscal_bot.fiscal_api import build_receipt_request
from fiscal_bot.settings import REQUEST_DOC_VERSION
from unittest.mock import patch, Mock
import unittest


class ReceiptTestCase(unittest.TestCase):

    @patch("fiscal_bot.fiscal_api.get_monthly_increment_id")
    @patch("fiscal_bot.fiscal_api.get_daily_increment_id")
    def test_template_built(self, get_daily_increment_id_mock, get_monthly_increment_id_mock):
        get_monthly_increment_id_mock.return_value = 202
        get_daily_increment_id_mock.return_value = 2

        with patch("fiscal_bot.fiscal_api.get_now") as get_now_mock:
            get_now_mock.return_value = datetime(2017, 12, 31, 12, 0, 5)
            filename, content = build_receipt_request(
                task=Mock(),
                tenderID="UA-2019-01-31-000147-a",
                lot_index=None,
                identifier="AA426097",
                name="Python Monty Иванович",
            )
        get_monthly_increment_id_mock.assert_called_once()
        get_daily_increment_id_mock.assert_called_once()
        self.assertEqual(
            filename,
            "2659" "0002426097" "J16031" "{0:02d}".format(REQUEST_DOC_VERSION) + "1000000202" "1" "12" "2017" "2659.xml"
        )

        self.assertIn(b"<HNUM>2</HNUM>", content)
        self.assertIn(b"<C_DOC_CNT>202</C_DOC_CNT>", content)
        self.assertIn("<C_DOC_VER>{}</C_DOC_VER>".format(REQUEST_DOC_VERSION).encode("windows-1251"), content)
        self.assertIn(b"<HFILL>31122017</HFILL>", content)
        self.assertIn(b"<HTIME>12:00:05</HTIME>", content)
        self.assertIn("<HNAME>ДП «ПРОЗОРРО»</HNAME>".encode("windows-1251"), content)
        self.assertIn(b"<HTIN>02426097</HTIN>", content)
        self.assertIn(b"<HKSTI>2659</HKSTI>", content)
        self.assertIn("<HSTI>ДПI у Шевченківському районі ГУ ДФС у м. Києві</HSTI>".encode("windows-1251"), content)
        self.assertIn(b"<R0101G1S>UA-2019-01-31-000147-a</R0101G1S>", content)
        self.assertIn(b"<R0201G1S>AA426097</R0201G1S>", content)
        self.assertIn("<R0202G1S>Python Monty Иванович</R0202G1S>".encode("windows-1251"), content)
        self.assertIn("<R0203G1S>Python</R0203G1S>".encode("windows-1251"), content)
        self.assertIn("<R0204G1S>Monty</R0204G1S>".encode("windows-1251"), content)
        self.assertIn("<R0205G1S>Иванович</R0205G1S>".encode("windows-1251"), content)

    @patch("fiscal_bot.fiscal_api.get_monthly_increment_id")
    @patch("fiscal_bot.fiscal_api.get_daily_increment_id")
    def test_template_built_lot(self, get_daily_increment_id_mock, get_monthly_increment_id_mock):
        get_monthly_increment_id_mock.return_value = 202
        get_daily_increment_id_mock.return_value = 2

        with patch("fiscal_bot.fiscal_api.get_now") as get_now_mock:
            get_now_mock.return_value = datetime(2017, 12, 31, 12, 0, 5)
            filename, content = build_receipt_request(
                task=Mock(),
                tenderID="UA-2019-01-31-000147-a",
                lot_index=0,
                identifier="AA426097",
                name="Python Monty Иванович",
            )
        get_monthly_increment_id_mock.assert_called_once()
        get_daily_increment_id_mock.assert_called_once()
        self.assertIn("<R0101G1S>UA-2019-01-31-000147-a Лот 1</R0101G1S>".encode("windows-1251"), content)

    @patch("fiscal_bot.fiscal_api.get_monthly_increment_id")
    @patch("fiscal_bot.fiscal_api.get_daily_increment_id")
    def test_template_built_legal_entity(self, get_daily_increment_id_mock, get_monthly_increment_id_mock):
        get_monthly_increment_id_mock.return_value = 13
        get_daily_increment_id_mock.return_value = 12

        with patch("fiscal_bot.fiscal_api.get_now") as get_now_mock:
            get_now_mock.return_value = datetime(2017, 12, 31, 12, 0, 5)
            filename, content = build_receipt_request(
                task=Mock(),
                tenderID="UA-2019-01-31-000147-a",
                lot_index=None,
                identifier="12426097",
                name="ПП `Python Monty Иванович`",
            )
        get_monthly_increment_id_mock.assert_called_once()
        get_daily_increment_id_mock.assert_called_once()
        self.assertEqual(
            filename,
            "2659" "0002426097" "J16031" "{0:02d}".format(REQUEST_DOC_VERSION) + "1" 
            "00" "0000013" "1" "12" "2017" "2659.xml"
        )

        self.assertIn(b"<HNUM>12</HNUM>", content)
        self.assertIn(b"<C_DOC_CNT>13</C_DOC_CNT>", content)
        self.assertIn(b"<HFILL>31122017</HFILL>", content)
        self.assertIn(b"<HTIME>12:00:05</HTIME>", content)
        self.assertIn("<HNAME>ДП «ПРОЗОРРО»</HNAME>".encode("windows-1251"), content)
        self.assertIn(b"<HTIN>02426097</HTIN>", content)
        self.assertIn(b"<HKSTI>2659</HKSTI>", content)
        self.assertIn("<HSTI>ДПI у Шевченківському районі ГУ ДФС у м. Києві</HSTI>".encode("windows-1251"), content)
        self.assertIn(b"<R0101G1S>UA-2019-01-31-000147-a</R0101G1S>", content)
        self.assertIn(b"<R0201G1S>12426097</R0201G1S>", content)
        self.assertIn("<R0202G1S>ПП `Python Monty Иванович`</R0202G1S>".encode("windows-1251"), content)
        self.assertNotIn("<R0203G1S>".encode("windows-1251"), content)
        self.assertNotIn("<R0204G1S>".encode("windows-1251"), content)
        self.assertNotIn("<R0205G1S>".encode("windows-1251"), content)

    @patch("fiscal_bot.fiscal_api.FISCAL_BOT_ENV_NUMBER", 9)
    @patch("fiscal_bot.fiscal_api.get_monthly_increment_id")
    @patch("fiscal_bot.fiscal_api.get_daily_increment_id")
    def test_template_built_sandbox(self, get_daily_increment_id_mock, get_monthly_increment_id_mock):
        get_monthly_increment_id_mock.return_value = 202
        get_daily_increment_id_mock.return_value = 2

        with patch("fiscal_bot.fiscal_api.get_now") as get_now_mock:
            get_now_mock.return_value = datetime(2017, 12, 31, 12, 0, 5)
            filename, content = build_receipt_request(
                task=Mock(),
                tenderID="UA-2019-01-31-000147-a",
                lot_index=None,
                identifier="AA426097",
                name="Python Monty Иванович",
            )
        get_monthly_increment_id_mock.assert_called_once()
        get_daily_increment_id_mock.assert_called_once()
        self.assertEqual(
            filename,
            "2659" "0002426097" "J16031" "{0:02d}".format(REQUEST_DOC_VERSION) + "100" 
            "9" "000202" "1" "12" "2017" "2659.xml"
        )
