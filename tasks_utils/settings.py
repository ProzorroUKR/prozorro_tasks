import requests

from environment_settings import USER_AGENT

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)

DEFAULT_HEADERS = {
    "User-agent": USER_AGENT
}
