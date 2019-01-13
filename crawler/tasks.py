from celery.utils.log import get_task_logger
from celery_worker.celery import app
from crawler.settings import (
    CONNECT_TIMEOUT, READ_TIMEOUT, API_LIMIT, API_OPT_FIELDS,
    DEFAULT_RETRY_AFTER, FEED_URL_TEMPLATE, WAIT_MORE_RESULTS_COUNTDOWN
)
from environment_settings import PUBLIC_API_HOST, API_VERSION
from edr_bot.handlers import edr_bot_tender_handler
import requests


logger = get_task_logger(__name__)


# ITEM_HANDLERS contains code that will be executed for every feed item
# these functions SHOULD NOT use database/API/any other IO calls
# handlers can add new tasks to the queue
# example: if(item["status"] == "awarding"){ attach_edr_yaml.delay(item["id"]) }

ITEM_HANDLERS = [
    edr_bot_tender_handler,
]

RETRY_REQUESTS_EXCEPTIONS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


@app.task(bind=True)
def echo_task(self, v=0):  # pragma: no cover
    """
    DEBUG Task
    :param self:
    :param v:
    :return:
    """
    from time import sleep
    for i in reversed(range(10)):
        print((v, i))
        sleep(3)
    print("Add new task")
    echo_task.delay(v+1)
    print("#$" * 10)


@app.task(bind=True, acks_late=True)
def process_feed(self, resource="tenders", offset="", descending="", cookies=None):

    if not offset:  # initialization
        descending = "1"

    url = FEED_URL_TEMPLATE.format(
            host=PUBLIC_API_HOST,
            version=API_VERSION,
            resource=resource,
            descending=descending,
            offset=offset,
            limit=API_LIMIT,
            opt_fields="%2C".join(API_OPT_FIELDS)
          )

    try:
        response = requests.get(
            url,
            cookies=requests.utils.cookiejar_from_dict(cookies or {}),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
    except RETRY_REQUESTS_EXCEPTIONS as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:
        if response.status_code == 200:
            response_json = response.json()
            for item in response_json["data"]:
                for handler in ITEM_HANDLERS:
                    try:
                        handler(item)
                    except Exception as e:
                        logger.exception(e)

            # handle cookies
            if response.cookies:
                cookies = requests.utils.dict_from_cookiejar(response.cookies)

            # schedule getting the next page
            next_page_kwargs = dict(
                offset=response_json["next_page"]["offset"],
                descending=descending,
                cookies=cookies
            )
            if len(response_json["data"]) < API_LIMIT:
                if descending:
                    logger.info("Stopping backward crawling")
                else:
                    process_feed.apply_async(
                        kwargs=next_page_kwargs,
                        countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                    )
            else:
                process_feed.apply_async(kwargs=next_page_kwargs)

            if not offset:  # if it's initialization, add forward crawling task
                process_feed.apply_async(
                    kwargs=dict(
                        offset=response_json["prev_page"]["offset"],
                        cookies=cookies
                    ),
                    countdown=WAIT_MORE_RESULTS_COUNTDOWN,
                )
        elif response.status_code == 412:  # Precondition failed
            logger.warning("Precondition failed with cookies {}".format(cookies))
            retry_kwargs = dict(**self.request.kwargs)
            retry_kwargs["cookies"] = requests.utils.dict_from_cookiejar(response.cookies)
            raise self.retry(kwargs=retry_kwargs)

        elif response.status_code == 404:  # "Offset expired/invalid"
            logger.warning("Offset {} failed with cookies {}".format(offset, cookies))

            if not descending:  # for forward process only
                logger.info("Feed process reinitialization")
                retry_kwargs = {k: v for k, v in self.request.kwargs.items()
                                if k != "offset"}
                raise self.retry(kwargs=retry_kwargs)

        else:
            raise self.retry(countdown=response.headers.get('Retry-After', DEFAULT_RETRY_AFTER))

        return response.status_code
