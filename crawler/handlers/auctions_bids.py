from pymongo import MongoClient
from celery.utils.log import get_task_logger
from crawler.settings import TIMEZONE
from celery_worker.celery import app
from crawler.settings import CONNECT_TIMEOUT, READ_TIMEOUT
from dateutil import parser
from datetime import datetime, timedelta
import requests
import random
import os


logger = get_task_logger(__name__)


def get_now():
    return datetime.now(tz=TIMEZONE)


def get_collection():
    client = MongoClient(
        host='mongo',
        port=27017,
        username=os.environ.get("MONGO_USER_NAME"),
        password=os.environ.get("MONGO_PASSWORD")
    )
    db = client.auctions_bids
    return db.auctions


def auction_bids_handler(tender_data):
    if tender_data["status"] != "complete":
        return

    if tender_data["procurementMethodType"] == "reporting":
        return

    lots = tender_data.get("lots", [])
    if not lots:
        lots = [{}]

    for lot in lots:
        save_auction_statistics.delay(
            "_".join(filter(None, (tender_data["id"], lot.get("id"))))
        )


@app.task(bind=True)
def save_auction_statistics(self, auction_id):
    try:
        response = requests.get(
            "https://auction.openprocurement.org/database/{}".format(auction_id),
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        logger.exception(exc)
        raise self.retry(exc=exc)

    response_json = response.json()

    if "error" in response_json:
        return

    decreases = []
    bids = {
        e["bidder_id"]: {"amount": e["amount"]}
        for e in response_json["initial_bids"]
    }

    for stage in response_json["stages"]:
        if "bidder_id" in stage:
            if stage["amount"] != bids[stage["bidder_id"]]["amount"]:
                difference = bids[stage["bidder_id"]]["amount"] - stage["amount"]
                percentage = difference / bids[stage["bidder_id"]]["amount"]

                decreases.append(
                    dict(
                        before=bids[stage["bidder_id"]]["amount"],
                        after=stage["amount"],
                        bidder_id=stage["bidder_id"],
                        difference=difference,
                        percentage=percentage,
                    )
                )
                bids[stage["bidder_id"]]["amount"] = stage["amount"]

    if decreases:
        doc = {"_id": auction_id, "data": decreases}
        get_collection().insert_one(doc)
