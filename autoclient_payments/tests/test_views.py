from datetime import datetime
from unittest.mock import patch

from app.tests.base import BaseTestCase


AVAILABLE_HEALTH = {
    "status": "available",
    "cdb_public": {"status": "available"},
    "cdb_lb": {"status": "available"},
    "cdb_search": {"status": "available"},
    "liqpay": {"status": "available"},
    "autoclient": {"status": "available"},
    "mongodb": {"status": "available"},
    "rabbitmq": {"status": "available"},
}

UNAVAILABLE_HEALTH = {
    **AVAILABLE_HEALTH,
    "status": "unavailable",
    "autoclient": {"status": "unavailable"},
}


class HealthCheckTestCase(BaseTestCase):
    @patch("autoclient_payments.views.views.save_health_data")
    @patch("autoclient_payments.views.views.health")
    def test_healthcheck_available(self, health_mock, save_health_data_mock):
        health_mock.return_value = AVAILABLE_HEALTH

        response = self.client.get("/autoclient_payments/healthcheck")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, AVAILABLE_HEALTH)
        health_mock.assert_called_once_with()
        save_health_data_mock.assert_called_once_with(AVAILABLE_HEALTH)

    @patch("autoclient_payments.views.views.save_health_data")
    @patch("autoclient_payments.views.views.health")
    def test_healthcheck_unavailable(self, health_mock, save_health_data_mock):
        health_mock.return_value = UNAVAILABLE_HEALTH

        response = self.client.get("/autoclient_payments/healthcheck")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json, UNAVAILABLE_HEALTH)
        save_health_data_mock.assert_called_once_with(UNAVAILABLE_HEALTH)

    @patch("autoclient_payments.views.views.get_health_data")
    @patch("autoclient_payments.views.views.save_health_data")
    @patch("autoclient_payments.views.views.health")
    def test_healthcheck_historical_when_unavailable(
        self, health_mock, save_health_data_mock, get_health_data_mock
    ):
        health_mock.return_value = UNAVAILABLE_HEALTH
        created_at = datetime(2026, 1, 1, 12, 0, 0)
        get_health_data_mock.return_value = [{
            "data": AVAILABLE_HEALTH,
            "createdAt": created_at,
        }]

        response = self.client.get("/autoclient_payments/healthcheck?historical=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {
            **UNAVAILABLE_HEALTH,
            "historical": [{
                "data": AVAILABLE_HEALTH,
                "timestamp": int(created_at.timestamp() * 1000),
            }],
        })
