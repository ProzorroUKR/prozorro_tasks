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

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://public.api.openprocurement.org")
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
SPREAD_TENDER_TASKS_INTERVAL = float(os.environ.get("EDR_BOT_SPREAD_TENDER_TASKS_INTERVAL", "30"))


API_SIGN_HOST = os.environ.get("API_SIGN_HOST", "http://host.docker.internal:6543")
API_SIGN_USER = os.environ.get("API_SIGN_USER", "test")
API_SIGN_PASSWORD = os.environ.get("API_SIGN_PASSWORD", "test")

FISCAL_API_HOST = os.environ.get("FISCAL_API_HOST", "https://cabinet.sfs.gov.ua")
FISCAL_API_PROXIES = dict()
if os.environ.get("FISCAL_API_HTTP_PROXY"):
    FISCAL_API_PROXIES["http"] = os.environ.get("FISCAL_API_HTTP_PROXY")
if os.environ.get("FISCAL_API_HTTPS_PROXY"):
    FISCAL_API_PROXIES["https"] = os.environ.get("FISCAL_API_HTTPS_PROXY")
FISCAL_API_PROXIES = FISCAL_API_PROXIES or None
FISCAL_SENDER_TIN = os.environ.get("FISCAL_SENDER_TIN", "02426097")
FISCAL_SENDER_NAME = os.environ.get("FISCAL_SENDER_NAME", "ДП «ПРОЗОРРО»")
FISCAL_SENDER_STI = os.environ.get("FISCAL_SENDER_STI", "ДПI у Шевченківському районі ГУ ДФС у м. Києві")
# as long as the fiscal api doesn't provide any test environments
# and it has it's counter that we have to send and increment with every request
# we've decided to use the counter first sign to distinct our requests from different environments
# for prod the will be 0000001, 0000002, ..., for sandbox -  9000001, 9000002, ...
FISCAL_BOT_ENV_NUMBER = int(os.environ.get("FISCAL_BOT_ENV_NUMBER", 0))

SENTRY_DSN = os.environ.get("SENTRY_DSN", None)
SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", None)

APP_AUTH_FILE = os.environ.get("APP_AUTH_FILE", None)
APP_AUIP_FILE = os.environ.get("APP_AUIP_FILE", None)
APP_AUIP_ENABLED = os.environ.get("APP_AUIP_ENABLED", False)

APP_X_FORWARDED_NUMBER = int(os.environ.get("APP_X_FORWARDED_NUMBER", 0))

LIQPAY_API_HOST = os.environ.get("LIQPAY_API_HOST", "https://www.liqpay.ua")
LIQPAY_API_PROXIES = dict()
if os.environ.get("LIQPAY_API_HTTP_PROXY"):
    LIQPAY_API_PROXIES["http"] = os.environ.get("LIQPAY_API_HTTP_PROXY")
if os.environ.get("LIQPAY_API_HTTPS_PROXY"):
    LIQPAY_API_PROXIES["https"] = os.environ.get("LIQPAY_API_HTTPS_PROXY")
LIQPAY_PUBLIC_KEY = os.environ.get("LIQPAY_PUBLIC_KEY", "")
LIQPAY_PRIVATE_KEY = os.environ.get("LIQPAY_PRIVATE_KEY", "")
LIQPAY_SANDBOX_PUBLIC_KEY = os.environ.get("LIQPAY_SANDBOX_PUBLIC_KEY", "")
LIQPAY_SANDBOX_PRIVATE_KEY = os.environ.get("LIQPAY_SANDBOX_PRIVATE_KEY", "")
LIQPAY_SANDBOX_BY_DEFAULT_ENABLED = os.environ.get("LIQPAY_SANDBOX_BY_DEFAULT_ENABLED", False)
LIQPAY_TAX_PERCENTAGE = float(os.environ.get("LIQPAY_TAX_PERCENTAGE", 0))

PORTAL_HOST = os.environ.get("PORTAL_HOST", "https://prozorro.gov.ua")

TREASURY_INT_START_DATE = os.environ.get("TREASURY_INT_START_DATE", "2020-03-27")
TREASURY_WSDL_URL = os.environ.get(
    "TREASURY_WSDL_URL", "http://46.164.148.178:24310/bars.webservices.prozorro/prozorro/prozorroapi.asmx?WSDL")
TREASURY_USER = os.environ.get("TREASURY_USER", "prozorrouser")
TREASURY_PASSWORD = os.environ.get("TREASURY_PASSWORD", "111111")
TREASURY_SKIP_REQUEST_VERIFY = os.environ.get("TREASURY_SKIP_REQUEST_VERIFY", False)
TREASURY_RESPONSE_RETRY_COUNTDOWN = int(os.environ.get("TREASURY_RESPONSE_RETRY_COUNTDOWN", 600))
TREASURY_CATALOG_UPDATE_RETRIES = int(os.environ.get("TREASURY_CATALOG_UPDATE_RETRIES", 100))
TREASURY_DB_NAME = os.environ.get("TREASURY_DB_NAME", "treasury")
TREASURY_CONTEXT_COLLECTION = os.environ.get("TREASURY_CONTEXT_COLLECTION", "treasury_sent_states")
TREASURY_ORG_COLLECTION = os.environ.get("TREASURY_ORG_COLLECTION", "organisations")
TREASURY_OBLIGATION_COLLECTION = os.environ.get("TREASURY_OBLIGATION_COLLECTION", "obligations")
TREASURY_DATETIME_FMT = os.environ.get("TREASURY_DATETIME_FMT", "%Y-%m-%dT%H:%M:%S")
