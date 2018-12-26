from celery.utils.log import get_task_logger
from celery_worker.celery import app
from crawler.settings import CONNECT_TIMEOUT, READ_TIMEOUT, API_LIMIT, API_OPT_FIELDS
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


@app.task(bind=True, acks_late=True)
def process_feed(self, resource="tenders", offset="", descending="", cookies=None):

    if not offset:  # initialization
        descending = "1"

    url = "{host}/api/{version}/{resource}?feed=changes&" \
          "descending={descending}&offset={offset}&limit={limit}&opt_fields={opt_fields}".format(
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
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)
    else:
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
        if len(response_json["data"]) < API_LIMIT:
            if not descending:
                process_feed.apply_async(
                    kwargs=dict(
                        offset=response_json["next_page"]["offset"],
                        descending=descending,
                        cookies=cookies
                    ),
                    countdown=60,
                )
        else:
            process_feed.delay(
                offset=response_json["next_page"]["offset"],
                descending=descending,
                cookies=cookies
            )

        if not offset:  # if it's initialization
            process_feed.apply_async(
                kwargs=dict(
                    offset=response_json["prev_page"]["offset"],
                    cookies=cookies
                ),
                countdown=60,
            )

        return response.status_code
