import requests

from uuid import uuid4

from tasks_utils.settings import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
)
from environment_settings import (
    API_VERSION,
    API_TOKEN,
    API_HOST,
)

from app.logging import getLogger

logger = getLogger()


def get_cookies():
    client_request_id = uuid4().hex
    head_response = requests.head(
        "{host}/api/{version}/spore".format(
            host=API_HOST,
            version=API_VERSION,
        ),
        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        headers={
            "Authorization": "Bearer {}".format(API_TOKEN),
            "X-Client-Request-ID": client_request_id,
        }
    )
    return head_response.cookies.get_dict()
