import pytz
import os

TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Europe/Kiev"))

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://public.api.openprocurement.org")
API_HOST = os.environ.get("API_HOST", "https://lb.api.openprocurement.org")
API_VERSION = os.environ.get("API_VERSION", "2.4")
API_TOKEN = os.environ.get("API_TOKEN", "robot")

DS_HOST = os.environ.get("DS_HOST", "https://upload-docs.prozorro.org")
DS_PORT = os.environ.get("DS_PORT", "80")
DS_USER = os.environ.get("DS_USER", "robot")
DS_PASSWORD = os.environ.get("DS_PASSWORD", "robot")

EDR_API_HOST = os.environ.get("EDR_API_HOST", "http://127.0.0.1")
EDR_API_PORT = os.environ.get("EDR_API_PORT", "80")
EDR_API_VERSION = os.environ.get("EDR_API_VERSION", "1.0")
EDR_API_USER = os.environ.get("EDR_API_USER", "robot")
EDR_API_PASSWORD = os.environ.get("EDR_API_PASSWORD", "robot")
