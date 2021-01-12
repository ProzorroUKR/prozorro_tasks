from tasks_utils.requests import get_filename_from_response
from unittest.mock import Mock
import unittest


class ResultsDBTestCase(unittest.TestCase):

    def test_simple(self):
        response = Mock(headers={
            "content-disposition": "attachment; filename=sign.p7s",
            "User-agent": "prozorro_tasks",
        })
        filename = get_filename_from_response(response)
        self.assertEqual(filename, "sign.p7s")

    def test_encoded(self):
        response = Mock(headers={
            "content-disposition":
            "attachment; filename=%D0%A7%D0%B5%D1%80%D0%BD%D1%96%D0%B3%D1%96%D0%B2%D0%BA%D0%B0.pdf;"
            " filename*=utf-8''%D0%A7%D0%B5%D1%80%D0%BD%D1%96%D0%B3%D1%96%D0%B2%D0%BA%D0%B0.pdf",
            "User-agent": "prozorro_tasks",
        })
        filename = get_filename_from_response(response)
        self.assertEqual(filename, "Чернігівка.pdf")
