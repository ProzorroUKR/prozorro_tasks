from celery.utils.log import get_task_logger
from celery_worker.celery import app
from celery_worker.locks import unique_task_decorator
from crawler.settings import (
    CONNECT_TIMEOUT, READ_TIMEOUT, API_LIMIT, API_OPT_FIELDS,
    FEED_URL_TEMPLATE, WAIT_MORE_RESULTS_COUNTDOWN
)
from environment_settings import PUBLIC_API_HOST, API_VERSION, CRAWLER_TENDER_HANDLERS
from edr_bot.handlers import edr_bot_tender_handler
from edr_bot.utils import get_request_retry_countdown
from fiscal_bot.handlers import fiscal_bot_tender_handler
import requests


logger = get_task_logger(__name__)


# ITEM_HANDLERS contains code that will be executed for every feed item
# these functions SHOULD NOT use database/API/any other IO calls
# handlers can add new tasks to the queue
# example: if(item["status"] == "awarding"){ attach_edr_yaml.delay(item["id"]) }

ITEM_HANDLERS = [
    edr_bot_tender_handler,
    fiscal_bot_tender_handler,
]
if CRAWLER_TENDER_HANDLERS:
    logger.info("Filtering tender handler with provided set: {}".format(CRAWLER_TENDER_HANDLERS))
    ITEM_HANDLERS = [i for i in ITEM_HANDLERS if i.__name__ in CRAWLER_TENDER_HANDLERS]

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True)
@unique_task_decorator
def echo_task(self, v=0):  # pragma: no cover
    """
    DEBUG Task
    :param self:
    :param v:
    :return:
    """
    from time import sleep
    for i in reversed(range(10)):
        logger.info((v, i), extra={"MESSAGE_ID": "COUNTDOWN"})
        sleep(3)
    logger.info("Add new task",  extra={"MESSAGE_ID": "Hi"})
    echo_task.delay(v+1)
    logger.info("#$" * 10,  extra={"MESSAGE_ID": "Bye"})


@app.task(bind=True, acks_late=True, max_retries=None)
@unique_task_decorator
def process_feed(self, resource="tenders", offset="", descending="", mode="_all_", cookies=None, try_count=0):
    logger.info("Start task {}".format(self.request.id),
                extra={"MESSAGE_ID": "START_TASK_MSG", "TASK_ID": self.request.id})

    if not offset:  # initialization
        descending = "1"

    url = FEED_URL_TEMPLATE.format(
            host=PUBLIC_API_HOST,
            version=API_VERSION,
            resource=resource,
            descending=descending,
            offset=offset,
            limit=API_LIMIT,
            opt_fields="%2C".join(API_OPT_FIELDS),
            mode=mode,
          )

    try:
        response = requests.get(
            url,
            cookies=requests.utils.cookiejar_from_dict(cookies or {}),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc, extra={"MESSAGE_ID": "FEED_RETRY_EXCEPTION"})
        raise self.retry(exc=exc)
    else:
        if response.status_code == 200:
            response_json = response.json()
            for item in response_json["data"]:
                for handler in ITEM_HANDLERS:
                    try:
                        handler(item)
                    except Exception as e:
                        logger.exception(e, extra={"MESSAGE_ID": "FEED_HANDLER_EXCEPTION"})

            # handle cookies
            if response.cookies:
                cookies = requests.utils.dict_from_cookiejar(response.cookies)

            # schedule getting the next page
            next_page_kwargs = dict(
                mode=mode,
                offset=response_json["next_page"]["offset"],
                descending=descending,
                cookies=cookies
            )
            if len(response_json["data"]) < API_LIMIT:
                if descending:
                    logger.info("Stopping backward crawling", extra={"MESSAGE_ID": "FEED_BACKWARD_FINISH"})
                else:
                    if offset == next_page_kwargs["offset"]:
                        next_page_kwargs["try_count"] = try_count + 1
                    result = process_feed.apply_async(
                        kwargs=next_page_kwargs,
                        countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                    )
                    logger.info("Planned task {}".format(result.id),
                                extra={"MESSAGE_ID": "PLAN_TASK_MSG", "PLANNED_TASK_ID": result.id})
            else:
                result = process_feed.apply_async(kwargs=next_page_kwargs)
                logger.info("Planned task {}".format(result.id),
                            extra={"MESSAGE_ID": "PLAN_TASK_MSG", "PLANNED_TASK_ID": result.id})

            # if it's initialization, add forward crawling task
            if not offset:
                process_kwargs = dict(
                    mode=mode,
                    cookies=cookies,
                )
                if response_json.get("prev_page", {}).get("offset"):
                    process_kwargs["offset"] = response_json["prev_page"]["offset"]
                else:
                    logger.debug("Initialization on an empty feed result", extra={"MESSAGE_ID": "FEED_INIT_EMPTY"})
                    process_kwargs["offset"] = ""
                    process_kwargs["try_count"] = try_count + 1

                result = process_feed.apply_async(
                    kwargs=process_kwargs,
                    countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                )
                logger.info("Planned task {}".format(result.id),
                            extra={"MESSAGE_ID": "PLAN_TASK_MSG", "PLANNED_TASK_ID": result.id})
        elif response.status_code == 412:  # Precondition failed
            logger.warning("Precondition failed with cookies {}".format(cookies),
                           extra={"MESSAGE_ID": "FEED_PRECONDITION_FAILED"})
            retry_kwargs = dict(**self.request.kwargs)
            retry_kwargs["cookies"] = requests.utils.dict_from_cookiejar(response.cookies)
            raise self.retry(kwargs=retry_kwargs)

        elif response.status_code == 404:  # "Offset expired/invalid"
            logger.warning("Offset {} failed with cookies {}".format(offset, cookies),
                           extra={"MESSAGE_ID": "FEED_OFFSET_FAILED"})

            if not descending:  # for forward process only
                logger.info("Feed process reinitialization",
                            extra={"MESSAGE_ID": "FEED_REINITIALIZATION"})
                retry_kwargs = {k: v for k, v in self.request.kwargs.items()
                                if k != "offset"}
                raise self.retry(kwargs=retry_kwargs)

        else:
            logger.warning("Unexpected status code {}: {}".format(response.status_code, response.text),
                           extra={"MESSAGE_ID": "FEED_UNEXPECTED_STATUS"})
            raise self.retry(countdown=get_request_retry_countdown(response))

        return response.status_code
