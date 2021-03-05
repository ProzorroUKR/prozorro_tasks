import requests

from celery.utils.log import get_task_logger

from celery_worker.celery import app
from celery_worker.locks import unique_lock
from crawler.settings import (
    CONNECT_TIMEOUT,
    READ_TIMEOUT,
    API_LIMIT,
    FEED_URL_TEMPLATE,
    WAIT_MORE_RESULTS_COUNTDOWN,
)
from crawler.utils import (
    put_date_modified_lock,
    update_date_modified_lock,
    handle_date_modified_lock,
)
from environment_settings import (
    PUBLIC_API_HOST,
    API_VERSION,
)
from tasks_utils.requests import get_request_retry_countdown

from crawler import resources
from tasks_utils.settings import DEFAULT_HEADERS

logger = get_task_logger(__name__)


RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True, acks_late=True, lazy=False, max_retries=None)
@unique_lock(omit=("cookies",))
def process_feed(self, resource="tenders", offset=None, descending=None, mode="_all_", cookies=None, try_count=0):
    config = resources.configs.get(resource)

    cookies = cookies or {}

    # for initialization: start with backward feed request
    if not offset:
        descending = "1"
        put_date_modified_lock(resource)

    url = FEED_URL_TEMPLATE.format(
        host=PUBLIC_API_HOST,
        version=API_VERSION,
        resource=resource,
    )

    params = dict(
        feed="changes",
        limit=API_LIMIT,
        mode=mode,
    )
    if config.opt_fields:
        params["opt_fields"] = ",".join(config.opt_fields)
    if descending:
        params["descending"] = descending
    if offset:
        params["offset"] = offset

    try:
        response = requests.get(
            url,
            params=params,
            cookies=cookies,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=DEFAULT_HEADERS,
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FEED_RETRY_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code == 200:
            # handle cookies
            if response.cookies:
                cookies = response.cookies.get_dict()

            # get response data
            response_json = response.json()
            data = response_json["data"]
            next_page_offset = response_json["next_page"]["offset"]
            prev_page_offset = response_json.get("prev_page", {}).get("offset")

            # call handlers
            item_handlers = config.handlers
            for item in data:
                for handler in item_handlers:
                    try:
                        handler(item)
                    except Exception as e:
                        logger.exception(e, extra={"MESSAGE_ID": "FEED_HANDLER_EXCEPTION"})

            # handle reinitialization with lock by dateModified
            date_modified_list = [item["dateModified"] for item in data if "dateModified" in item]
            if not descending:
                # save dateModified on forward crawling
                max_date_modified = max(date_modified_list) if date_modified_list else None
                update_date_modified_lock(resource, max_date_modified)
            elif descending and offset:
                # stop backward crawling when reach saved dateModified
                min_date_modified = min(date_modified_list) if date_modified_list else None
                if handle_date_modified_lock(resource, min_date_modified):
                    logger.info("Stopping backward crawling early", extra={"MESSAGE_ID": "FEED_BACKWARD_EARLY_FINISH"})
                    return

            # schedule getting the next page
            next_page_kwargs = dict(
                resource=resource,
                mode=mode,
                offset=next_page_offset,
                cookies=cookies,
            )
            if descending:
                next_page_kwargs["descending"] = descending
            if len(data) < API_LIMIT:
                if descending:
                    logger.info("Stopping backward crawling", extra={"MESSAGE_ID": "FEED_BACKWARD_FINISH"})
                else:
                    if offset == next_page_offset:
                        # increase try_count so task won't be stopped by unique_lock decorator
                        next_page_kwargs["try_count"] = try_count + 1
                    else:
                        # reset try_count to sync all duplicate tasks
                        # and let unique_lock decorator do it's job
                        next_page_kwargs.pop("try_count", None)
                    process_feed.apply_async(
                        kwargs=next_page_kwargs,
                        countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                    )
            else:
                process_feed.apply_async(kwargs=next_page_kwargs)

            # for initialization: add forward crawling task
            if not offset:
                process_kwargs = dict(
                    resource=resource,
                    mode=mode,
                    cookies=cookies,
                )
                if prev_page_offset:
                    process_kwargs["offset"] = prev_page_offset
                else:
                    logger.debug("Initialization on an empty feed result", extra={"MESSAGE_ID": "FEED_INIT_EMPTY"})
                    process_kwargs["try_count"] = try_count + 1

                process_feed.apply_async(
                    kwargs=process_kwargs,
                    countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                )
        elif response.status_code == 412:  # Precondition failed
            logger.warning("Precondition failed with cookies {}".format(cookies),
                           extra={"MESSAGE_ID": "FEED_PRECONDITION_FAILED"})
            # retry with new cookies that have updated SERVER_ID cookie
            retry_kwargs = dict(**self.request.kwargs)
            retry_kwargs["cookies"] = response.cookies.get_dict()
            raise self.retry(kwargs=retry_kwargs)

        elif response.status_code == 404:  # "Offset expired/invalid"
            logger.warning("Offset {} failed with cookies {}".format(offset, cookies),
                           extra={"MESSAGE_ID": "FEED_OFFSET_FAILED"})

            # for forward or initialization: start new initialization (empty offset)
            if not descending or not offset:
                logger.info("Feed process reinitialization",
                            extra={"MESSAGE_ID": "FEED_REINITIALIZATION"})
                retry_kwargs = dict(**self.request.kwargs)
                retry_kwargs.pop("offset", None)
                raise self.retry(kwargs=retry_kwargs)

        else:
            logger.warning("Unexpected status code {}: {}".format(response.status_code, response.text),
                           extra={"MESSAGE_ID": "FEED_UNEXPECTED_STATUS"})
            raise self.retry(countdown=get_request_retry_countdown(response))


