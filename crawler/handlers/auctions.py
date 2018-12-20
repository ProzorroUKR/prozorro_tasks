from pymongo import MongoClient
from crawler.settings import TIMEZONE
from celery_worker.celery import app
from dateutil import parser
from datetime import datetime, timedelta
import random
import os


def get_now():
    return datetime.now(tz=TIMEZONE)



def get_collection():
    client = MongoClient(
        host='mongo',
        port=27017,
        username=os.environ.get("MONGO_USER_NAME"),
        password=os.environ.get("MONGO_PASSWORD")
    )
    db = client.auctions_db
    return db.auctions


def auction_planning_handler(tender_data):
    if tender_data["status"] != "active.auction":
        return

    lots = tender_data.get("lots", [])
    if not lots:
        lots = [{"auctionPeriod": tender_data.get("auctionPeriod", "")}]

    for lot in lots:
        # if "startDate" in lot.get("auctionPeriod", ""):
        #     auction_start = parser.parse(tender_data["auctionPeriod"]["startDate"])

        auction_start = get_now() + timedelta(seconds=random.randint(2, 3600))

        if auction_start > get_now():
            process_auction.apply_async(
                kwargs=dict(
                    auction_id="_".join(filter(None, (tender_data["id"], lot.get("id")))),
                    start_date=auction_start,
                    planning=True
                ),
                eta=auction_start,
            )


@app.task(bind=True)
def process_auction(self, auction_id, start_date, planning=False, stage=0):
    collection = get_collection()
    db_filter = {"_id": auction_id}
    doc = collection.find_one(db_filter)

    doc_is_missing = doc is None
    if planning and not doc_is_missing:  # TODO RE-PLANNING LOGIC
        return

    if doc_is_missing:
        doc = {"_id": auction_id, "stages": []}

    if len(doc["stages"]):
        stage_start = doc["stages"][-1]["start"]
        if isinstance(stage_start, str):
            stage_start = parser.parse(stage_start)
        start = stage_start + timedelta(seconds=60 * 2)
    else:
        start = parser.parse(start_date)

    doc["current_stage"] = stage
    doc["stages"].append(
        dict(
            start=self.request.eta,
            actual_start=get_now(),
            stage=stage,
        )
    )

    if doc_is_missing:
        collection.insert_one(doc)
    else:
        collection.update_one(db_filter,
                              {
                                  "$push": {"stages": doc["stages"][-1]},
                                  "$set": {"current_stage": stage}
                              })

    if len(doc["stages"]) < 8:
        process_auction.apply_async(kwargs=dict(auction_id=auction_id,
                                                start_date=start_date,
                                                stage=stage + 1),
                                    eta=start)
