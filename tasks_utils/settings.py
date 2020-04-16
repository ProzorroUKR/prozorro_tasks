import requests


RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 30.0
DEFAULT_RETRY_AFTER = 5
EXPONENTIAL_RETRY_BASE = 5
EXPONENTIAL_RETRY_MAX = 60 * 60


