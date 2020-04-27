from app.app import app
import unittest


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
