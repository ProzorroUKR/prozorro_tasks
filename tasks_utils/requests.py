from tasks_utils.settings import DEFAULT_RETRY_AFTER, EXPONENTIAL_RETRY_BASE, EXPONENTIAL_RETRY_MAX
import re


def get_filename_from_response(response):
    disposition = response.headers.get('content-disposition')
    if disposition:
        file_name = re.findall("filename=(.+)", disposition)
        if file_name:
            return file_name[0]


def get_request_retry_countdown(request):
    try:
        countdown = float(request.headers.get('Retry-After'))
    except (TypeError, ValueError):
        countdown = DEFAULT_RETRY_AFTER
    return countdown


def get_exponential_request_retry_countdown(task, request):
    countdown = get_request_retry_countdown(request)
    retries = task.request.retries
    if retries:
        countdown += EXPONENTIAL_RETRY_BASE ** retries
    return min(countdown, EXPONENTIAL_RETRY_MAX)
