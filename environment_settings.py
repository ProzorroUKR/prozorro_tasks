import pytz
import os

TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Europe/Kiev"))

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://admin:mypass@rabbit:5672")

CRAWLER_TENDER_HANDLERS = set(i.strip() for i in os.environ.get("CRAWLER_TENDER_HANDLERS", "").split(",") if i.strip())

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://root:example@mongo:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "tasks")
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.environ.get("MONGODB_SERVER_SELECTION_TIMEOUT", 5))
MONGODB_CONNECT_TIMEOUT = int(os.environ.get("MONGODB_CONNECT_TIMEOUT", 5))
MONGODB_SOCKET_TIMEOUT = int(os.environ.get("MONGODB_SOCKET_TIMEOUT", 5))

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://public.api.openprocurement.gov.ua")
API_HOST = os.environ.get("API_HOST", "https://lb.api.openprocurement.org")
API_VERSION = os.environ.get("API_VERSION", "2.4")
API_TOKEN = os.environ.get("API_TOKEN", "robot")

DS_HOST = os.environ.get("DS_HOST", "https://upload-docs.prozorro.gov.ua")
DS_USER = os.environ.get("DS_USER", "bot")
DS_PASSWORD = os.environ.get("DS_PASSWORD", "bot")

EDR_API_HOST = os.environ.get("EDR_API_HOST", "http://127.0.0.1")  # should NOT end with "/"
EDR_API_PORT = os.environ.get("EDR_API_PORT", "80")
EDR_API_VERSION = os.environ.get("EDR_API_VERSION", "1.0")
EDR_API_USER = os.environ.get("EDR_API_USER", "robot")
EDR_API_PASSWORD = os.environ.get("EDR_API_PASSWORD", "robot")


API_SIGN_HOST = os.environ.get("API_SIGN_HOST", "http://host.docker.internal:6543")
API_SIGN_USER = os.environ.get("API_SIGN_USER", "test")
API_SIGN_PASSWORD = os.environ.get("API_SIGN_PASSWORD", "test")

FISCAL_API_HOST = os.environ.get("FISCAL_API_HOST", "https://cabinet.sfs.gov.ua")
FISCAL_SENDER_TIN = os.environ.get("FISCAL_SENDER_TIN", "1010101017")  # set "02426097" for ПРОЗОРРО
FISCAL_SENDER_NAME = os.environ.get("FISCAL_SENDER_NAME", "ДП «ПРОЗОРРО»")
FISCAL_SENDER_STI = os.environ.get("FISCAL_SENDER_STI", "ДПI у Шевченківському районі ГУ ДФС у м. Києві")
FISCAL_TEST_MODE = os.environ.get("FISCAL_TEST_MODE", False)
FISCAL_TEST_NAME = os.environ.get("FISCAL_TEST_NAME", "Мирний Олександр Максимович")
FISCAL_TEST_IDENTIFIER = os.environ.get("FISCAL_TEST_IDENTIFIER", "1010101017")
