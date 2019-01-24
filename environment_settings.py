import pytz
import os

TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Europe/Kiev"))

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://admin:mypass@rabbit:5672")

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://root:example@mongo:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "tasks")
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.environ.get("MONGODB_SERVER_SELECTION_TIMEOUT", 5))
MONGODB_CONNECT_TIMEOUT = int(os.environ.get("MONGODB_CONNECT_TIMEOUT", 5))
MONGODB_SOCKET_TIMEOUT = int(os.environ.get("MONGODB_SOCKET_TIMEOUT", 5))

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://public.api.openprocurement.org")
API_HOST = os.environ.get("API_HOST", "https://lb.api.openprocurement.org")
API_VERSION = os.environ.get("API_VERSION", "2.4")
API_TOKEN = os.environ.get("API_TOKEN", "robot")

DS_HOST = os.environ.get("DS_HOST", "https://upload-docs.prozorro.org")
DS_PORT = os.environ.get("DS_PORT", "80")
DS_USER = os.environ.get("DS_USER", "robot")
DS_PASSWORD = os.environ.get("DS_PASSWORD", "robot")

EDR_API_HOST = os.environ.get("EDR_API_HOST", "http://127.0.0.1")  # should NOT end with "/"
EDR_API_PORT = os.environ.get("EDR_API_PORT", "80")
EDR_API_VERSION = os.environ.get("EDR_API_VERSION", "1.0")
EDR_API_USER = os.environ.get("EDR_API_USER", "robot")
EDR_API_PASSWORD = os.environ.get("EDR_API_PASSWORD", "robot")
