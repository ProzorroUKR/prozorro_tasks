from uuid import uuid4

from app.tests.base import BaseTestCase
from unittest.mock import patch, Mock, ANY


from base64 import b64encode

from edr_bot.utils import MOCK_DATA_DETAILS, remove_null_fields
from environment_settings import EDR_API_DIRECT_VERSION


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
                "status": "error",
                "errors": [
                    {
                        "location": "body",
                        "name": "data",
                        "description": [{"message": "Wrong name of the GET parameter. Code or passport is required"}],
                    }
                ]

            },
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.app.cache.get")
    @patch("app.app.cache.set")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.utils.get_edr_subject_details_data")
    def test_cached_response_for_bot(self, mock_get_edr_details_data, mock_get_edr_data, mock_cache_set, mock_cache_get):
        def fake_cache_get(key):
            if key == f"details_{EDR_API_DIRECT_VERSION}_123":
                return {"data": {"id": "1", "state": "1"}}
            elif key == f"details_{EDR_API_DIRECT_VERSION}_456":
                return {"data": {"id": "2", "state": "1"}}
            elif key == f"verify_{EDR_API_DIRECT_VERSION}_789":
                return {"data": [{"x_edrInternalId": "1"}, {"x_edrInternalId": "3"}]}
            return None

        mock_get_edr_details_data.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"test": 1}),
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
                'data': [{'test': 1}, {'test': 1}],
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

    @patch("app.app.cache.get")
    @patch("edr_bot.utils.get_edr_subject_data")
    @patch("edr_bot.utils.get_edr_subject_details_data")
    def test_cached_response_for_platform(self, mock_get_edr_details_data, mock_get_edr_data, mock_cache_get):
        def fake_cache_get(key):
            if key == f"verify_{EDR_API_DIRECT_VERSION}_123":
                return {"data": [{"x_edrInternalId": "2"},]}
            elif key == f"verify_{EDR_API_DIRECT_VERSION}_456":
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

    @patch("app.app.cache.get")
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
            response.json["errors"][0],
            {
                'description': [
                    {
                        "error": {
                            "errorDetails": "Couldn't find this code in EDR.",
                            "code": "notFound"
                        },
                        "meta": {"sourceDate": ANY},
                    }
                ],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 404)

        # non-detailed test data for platform
        code = "00037256"
        response = self.client.get(
            f'/edr/verify?code={code}',
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

        # details test data for robot version 1
        with patch("edr_bot.utils.EDR_API_DIRECT_VERSION", "1.0"):
            response = self.client.get(
                f'/edr/verify?code={code}',
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

        # details test data for robot version 2
        response = self.client.get(
            f'/edr/verify?code={code}',
            headers={'Authorization': basic_auth("robot", "robot")}
        )
        self.assertEqual(
            response.json,
            {
                'data': [remove_null_fields(MOCK_DATA_DETAILS[code][0])],
                'meta': {'detailsSourceDate': [ANY], 'sourceDate': ANY},
            }
        )
        self.assertEqual(response.status_code, 200)

    @patch("app.app.cache.get")
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
                "status": "error",
                "errors": [{
                    'description': [{'message': 'Service is disabled or upgrade.'}],
                    'location': 'body',
                    'name': 'data',
                }]
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
                "status": "error",
                "errors": [{
                    'description': [{'message': 'Retry request after 30 seconds.'}],
                    'location': 'body',
                    'name': 'data',
                }]
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
                "status": "error",
                "errors": [{
                    'description': [{'code': 11, 'message': '`passport` parameter has wrong value.'}],
                    'location': 'body',
                    'name': 'data',
                }]
            }
        )
        self.assertEqual(response.status_code, 403)

        mock_get_edr_data.return_value = Mock(
            status_code=404,
            json=Mock(return_value={
                'errors': [
                    {
                        "error": {
                            "errorDetails": "Couldn't find this code in EDR.",
                            "code": "notFound"
                        },
                    },
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
            response.json["errors"][0],
            {
                'description': [
                    {
                        "error": {
                            "errorDetails": "Couldn't find this code in EDR.",
                            "code": "notFound"
                        },
                    }
                ],
                'location': 'body',
                'name': 'data',
            }
        )
        self.assertEqual(response.status_code, 403)
