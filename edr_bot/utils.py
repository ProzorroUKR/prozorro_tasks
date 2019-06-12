from edr_bot.settings import DEFAULT_RETRY_AFTER
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def get_request_retry_countdown(request):
    try:
        countdown = float(request.headers.get('Retry-After'))
    except (TypeError, ValueError):
        countdown = DEFAULT_RETRY_AFTER
    return countdown
