import pytz
import os

TRUE_VARS =  (True, 'True', 'true', 'yes', '1', 1)

TIMEZONE = pytz.timezone(os.environ.get("TIMEZONE", "Europe/Kiev"))

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "amqp://admin:mypass@rabbit:5672")

def environ_list(name, sep=","):
    return [i.strip() for i in os.environ.get(name, "").split(sep) if i.strip()]

CONNECT_TIMEOUT = float(os.environ.get("CONNECT_TIMEOUT", 5.0))
READ_TIMEOUT = float(os.environ.get("READ_TIMEOUT", 30.0))
DEFAULT_RETRY_AFTER = int(os.environ.get("DEFAULT_RETRY_AFTER", 5))
EXPONENTIAL_RETRY_BASE = int(os.environ.get("EXPONENTIAL_RETRY_BASE", 5))
EXPONENTIAL_RETRY_MAX = int(os.environ.get("EXPONENTIAL_RETRY_MAX", 60 * 60))

CRAWLER_TENDER_HANDLERS = set(environ_list("CRAWLER_TENDER_HANDLERS"))
CRAWLER_CONTRACT_HANDLERS = set(environ_list("CRAWLER_CONTRACT_HANDLERS"))
CRAWLER_FRAMEWORK_HANDLERS = set(environ_list("CRAWLER_FRAMEWORK_HANDLERS"))

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://root:example@mongo:27017")
MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "tasks")
MONGODB_SERVER_SELECTION_TIMEOUT = int(os.environ.get("MONGODB_SERVER_SELECTION_TIMEOUT", 5))
MONGODB_CONNECT_TIMEOUT = int(os.environ.get("MONGODB_CONNECT_TIMEOUT", 5))
MONGODB_SOCKET_TIMEOUT = int(os.environ.get("MONGODB_SOCKET_TIMEOUT", 5))
MONGODB_MAX_POOL_SIZE = int(os.environ.get("MONGODB_MAX_POOL_SIZE", 100))

PUBLIC_API_HOST = os.environ.get("PUBLIC_API_HOST", "https://public.api.openprocurement.org")
API_HOST = os.environ.get("API_HOST", "https://lb.api.openprocurement.org")
API_VERSION = os.environ.get("API_VERSION", "2.4")
API_TOKEN = os.environ.get("API_TOKEN", "robot")

CHRONOGRAPH_API_TOKEN = os.environ.get("CHRONOGRAPH_API_TOKEN", "chronograph")

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
APP_AUIP_ENABLED = os.environ.get("APP_AUIP_ENABLED", False) in TRUE_VARS

APP_X_FORWARDED_NUMBER = int(os.environ.get("APP_X_FORWARDED_NUMBER", 0))

LIQPAY_API_HOST = os.environ.get("LIQPAY_API_HOST", "https://www.liqpay.ua")
LIQPAY_INTEGRATION_API_HOST = os.environ.get("LIQPAY_INTEGRATION_API_HOST", "https://prozoro.microaws.com")
LIQPAY_INTEGRATION_API_PATH = os.environ.get("LIQPAY_INTEGRATION_API_PATH", "api/v1/getRegistry")
LIQPAY_PROZORRO_ACCOUNT = os.environ.get("LIQPAY_PROZORRO_ACCOUNT")
LIQPAY_API_PROXIES = dict()
if os.environ.get("LIQPAY_API_HTTP_PROXY"):
    LIQPAY_API_PROXIES["http"] = os.environ.get("LIQPAY_API_HTTP_PROXY")
if os.environ.get("LIQPAY_API_HTTPS_PROXY"):
    LIQPAY_API_PROXIES["https"] = os.environ.get("LIQPAY_API_HTTPS_PROXY")
LIQPAY_PUBLIC_KEY = os.environ.get("LIQPAY_PUBLIC_KEY", "")
LIQPAY_PRIVATE_KEY = os.environ.get("LIQPAY_PRIVATE_KEY", "")
LIQPAY_SANDBOX_PUBLIC_KEY = os.environ.get("LIQPAY_SANDBOX_PUBLIC_KEY", "")
LIQPAY_SANDBOX_PRIVATE_KEY = os.environ.get("LIQPAY_SANDBOX_PRIVATE_KEY", "")
LIQPAY_SANDBOX_BY_DEFAULT_ENABLED = os.environ.get("LIQPAY_SANDBOX_BY_DEFAULT_ENABLED", False) in TRUE_VARS
LIQPAY_TAX_PERCENTAGE = float(os.environ.get("LIQPAY_TAX_PERCENTAGE", 0))

PAYMENTS_SKIP_TENDER_DAYS = int(os.environ.get("PAYMENTS_SKIP_TENDER_DAYS", 10))

PORTAL_HOST = os.environ.get("PORTAL_HOST", "https://prozorro.gov.ua")

TREASURY_INT_START_DATE = os.environ.get("TREASURY_INT_START_DATE", "2020-03-27")
TREASURY_WSDL_URL = os.environ.get("TREASURY_WSDL_URL",
                                   "http://46.164.148.178:24310/bars.webservices.dksu/prozorro/prozorroapi.asmx?WSDL")
TREASURY_USER = os.environ.get("TREASURY_USER", "prozorrouser")
TREASURY_PASSWORD = os.environ.get("TREASURY_PASSWORD", "111111")
TREASURY_SKIP_REQUEST_VERIFY = os.environ.get("TREASURY_SKIP_REQUEST_VERIFY", False) in TRUE_VARS
TREASURY_CATALOG_UPDATE_RETRIES = int(os.environ.get("TREASURY_CATALOG_UPDATE_RETRIES", 20))
TREASURY_PROCESS_TRANSACTION_RETRIES = int(os.environ.get("TREASURY_PROCESS_TRANSACTION_RETRIES", 10))
TREASURY_SEND_CONTRACT_XML_RETRIES = int(os.environ.get("TREASURY_SEND_CONTRACT_XML_RETRIES", 20))
TREASURY_DB_NAME = os.environ.get("TREASURY_DB_NAME", "treasury")
TREASURY_CONTEXT_COLLECTION = os.environ.get("TREASURY_CONTEXT_COLLECTION", "treasury_sent_states")
TREASURY_ORG_COLLECTION = os.environ.get("TREASURY_ORG_COLLECTION", "organisations")
TREASURY_XML_TEMPLATES_COLLECTION = os.environ.get("TREASURY_XML_TEMPLATES_COLLECTION", "xml_templates")
TREASURY_OBLIGATION_COLLECTION = os.environ.get("TREASURY_OBLIGATION_COLLECTION", "obligations")
TREASURY_DATETIME_FMT = os.environ.get("TREASURY_DATETIME_FMT", "%Y-%m-%dT%H:%M:%S")

CELERY_UI_EVENTS_MAX_WORKERS = int(os.environ.get("CELERY_UI_EVENTS_MAX_WORKERS", 5000))
CELERY_UI_EVENTS_MAX_TASKS = int(os.environ.get("CELERY_UI_EVENTS_MAX_TASKS", 10000))
