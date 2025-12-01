from uuid import uuid4

from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, ANY


from base64 import b64encode


def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
    return f'Basic {token}'


class MainApiTestCase(BaseTestCase):
    def test_permission_forbidden(self):
        response = self.client.get(
            '/edr/verify',
            headers={'Authorization': basic_auth("test", "test")}
        )
        self.assertEqual(
            response.data,
            b'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
            b'<title>401 Unauthorized</title>\n'
            b'<h1>Unauthorized</h1>\n'
            b'<p>Invalid username or password</p>\n'
        )
        self.assertEqual(response.status_code, 401)

    def test_params_is_required(self):
        response = self.client.get(
            '/edr/verify',
            headers={'Authorization': basic_auth("platform", "platform")}
        )
        self.assertEqual(
            response.json,
            {
                "location": "body",
                "name": "data",
                "description": [{"message": "Wrong name of the GET parameter. Code is required"}],
            },
        )
        self.assertEqual(response.status_code, 403)

    @patch("edr_bot.utils.cache.get")
    @patch("edr_bot.utils.cache.set")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.utils.get_edr_subject_details_data")
    def test_cached_response_for_bot(self, mock_get_edr_details_data, mock_get_edr_data, mock_cache_set, mock_cache_get):
        def fake_cache_get(key):
            if key == "details_123":
                return {"data": {"id": "1", "state": "1"}}
            elif key == "details_456":
                return {"data": {"id": "2", "state": "1"}}
            elif key == "verify_789":
                return {"data": [{"x_edrInternalId": "1"}, {"x_edrInternalId": "3"}]}
            return None

        mock_get_edr_details_data.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'data': [{"test": 1}]}),
            headers={
                'X-Request-ID': uuid4().hex,
                'User-agent': 'prozorro_tasks',
                'Date': 'Tue, 25 Dec 2018 19:00:00 UTC'
            }
        )
        mock_cache_get.side_effect = fake_cache_get
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {"data": {"id": "1", "state": "1"}}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            '/edr/verify?passport=456',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {"data": {"id": "2", "state": "1"}}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            '/edr/verify?code=789',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'data': [{'identification': {'scheme': 'UA-EDR'}}, {'identification': {'scheme': 'UA-EDR'}}],
                'meta': {
                    'detailsSourceDate': ['2018-12-25T19:00:00+00:00', '2018-12-25T19:00:00+00:00'],
                    'sourceDate': '2018-12-25T19:00:00+00:00'},
            }
        )
        self.assertEqual(response.status_code, 200)
        mock_get_edr_data.assert_not_called()
        mock_get_edr_details_data.assert_any_call("3")
        mock_get_edr_details_data.assert_any_call("1")
        mock_cache_set.assert_called_once()

    @patch("edr_bot.utils.cache.get")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.utils.get_edr_subject_details_data")
    def test_cached_response_for_platform(self, mock_get_edr_details_data, mock_get_edr_data, mock_cache_get):
        def fake_cache_get(key):
            if key == "verify_123":
                return {"data": [{"x_edrInternalId": "2"},]}
            elif key == "verify_456":
                return {"data": [{"x_edrInternalId": "1"}, {"x_edrInternalId": "3"}]}
            return None

        mock_cache_get.side_effect = fake_cache_get
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("platform", "platform")}
        )
        self.assertEqual(
            response.json,
            {'data': [{'x_edrInternalId': '2'}]}
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            '/edr/verify?passport=456',
            headers={'Authorization': basic_auth("platform", "platform")}
        )
        self.assertEqual(
            response.json,
            {"data": [{"x_edrInternalId": "1"}, {"x_edrInternalId": "3"}]}
        )
        mock_get_edr_data.assert_not_called()
        mock_get_edr_details_data.assert_not_called()

    @patch("edr_bot.utils.cache.get")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.views.SANDBOX_MODE")
    def test_get_sandbox_data(self, mock_sandbox_mode, mock_get_edr_data, mock_cache_get):
        mock_sandbox_mode.return_value = True
        mock_cache_get.return_value = None
        mock_get_edr_data.return_value = Mock(status_code=402)
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("platform", "platform")}
        )
        self.assertEqual(
            response.json,
            {
                'description': [{'message': 'Code 123 not found in test data for platform'}],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 404)

        # non-detailed test data for platform
        response = self.client.get(
            '/edr/verify?code=00037256',
            headers={'Authorization': basic_auth("platform", "platform")}
        )
        self.assertEqual(
            response.json,
            {
                'data': [{
                    'identification': {
                        'id': '00037256',
                        'legalName': 'ДЕРЖАВНЕ УПРАВЛІННЯ СПРАВАМИ',
                        'schema': 'UA-EDR',
                        'url': 'https://zqedr-api.nais.gov.ua/1.0/subjects/999186'
                    },
                    'registrationStatus': 'registered',
                    'registrationStatusDetails': 'зареєстровано',
                    'x_edrInternalId': 999186,
                }],
                'meta': {'sourceDate': ANY},
            }
        )
        self.assertEqual(response.status_code, 200)

        # details test data for robot
        response = self.client.get(
            '/edr/verify?code=00037256',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'data': [{
                    'activityKind': {
                        'description': 'Державне управління загального характеру',
                        'id': '84.11',
                        'scheme': 'КВЕД',
                    },
                    'address': {
                        'countryName': 'УКРАЇНА',
                        'postalCode': '01220',
                        'streetAddress': 'м.Київ, Печерський район ВУЛИЦЯ БАНКОВА буд. 11',
                    },
                    'founders': [{
                        'capital': 0,
                        'name': 'УКАЗ ПРИЗИДЕНТА УКРАЇНИ №278/2000 ВІД 23 ЛЮТОГО 2000 РОКУ',
                        'role': 4,
                        'role_text': 'засновник',
                    }],
                    'identification': {
                        'id': '00037256',
                        'legalName': 'ДЕРЖАВНЕ УПРАВЛІННЯ СПРАВАМИ',
                        'scheme': 'UA-EDR',
                    },
                    'management': 'КЕРІВНИК',
                    'name': 'ДЕРЖАВНЕ УПРАВЛІННЯ СПРАВАМИ',
                    'registrationStatus': 'registered',
                    'registrationStatusDetails': 'зареєстровано',
                }],
                'meta': {'detailsSourceDate': [ANY], 'sourceDate': ANY},
            }
        )
        self.assertEqual(response.status_code, 200)

    @patch("edr_bot.utils.cache.get")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.views.SANDBOX_MODE")
    def test_get_edr_data_errors(self, mock_sandbox_mode, mock_get_edr_data, mock_cache_get):
        mock_sandbox_mode.return_value = True
        mock_cache_get.return_value = None
        mock_get_edr_data.return_value = Mock(
            status_code=502,
            headers={'Content-Type': 'application/json'},
        )
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'description': [{'message': 'Service is disabled or upgrade.'}],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 403)

        mock_get_edr_data.return_value = Mock(
            status_code=429,
            headers={
                'Content-Type': 'application/json',
                'Retry-After': 30,
            },
        )
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'description': [{'message': 'Retry request after 30 seconds.'}],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 429)

        mock_get_edr_data.return_value = Mock(
            status_code=400,
            json=Mock(return_value={
                "errors": [{"code": 11, "message": "`passport` parameter has wrong value."}],
            }),
            headers={
                'Content-Type': 'application/json',
            },
        )
        response = self.client.get(
            '/edr/verify?passport=АБВ',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'description': [{'code': 11, 'message': '`passport` parameter has wrong value.'}],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 403)

        mock_get_edr_data.return_value = Mock(
            status_code=404,
            json=Mock(return_value={
                'errors': [
                    {
                        'description': [
                            {
                                "error": {
                                    "errorDetails": "Couldn't find this code in EDR.",
                                    "code": "notFound"
                                },
                            }
                        ]
                    }
                ]
            }),
            headers={
                'Content-Type': 'application/json',
            },
        )
        response = self.client.get(
            '/edr/verify?code=123',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'description': [
                    {
                        'description': [
                            {
                                "error": {
                                    "errorDetails": "Couldn't find this code in EDR.",
                                    "code": "notFound"
                                },
                            }
                        ]
                    }
                ],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 403)
