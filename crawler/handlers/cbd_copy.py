from pymongo import MongoClient
from celery_worker.celery import app
import os

print()


def get_collection():
    client = MongoClient(
        host='mongo',
        port=27017,
        username=os.environ.get("MONGO_USER_NAME"),
        password=os.environ.get("MONGO_PASSWORD")
    )
    db = client.local_cbd
    return db.tenders


@app.task
def save_tender(tender_data):
    uid = tender_data.pop("id")
    get_collection().update_one(
        dict(_id=uid),
        {"$set": {"_id": uid, "data": tender_data}},
        upsert=True
    )


def save_tender_handler(tender_data):
    save_tender.delay(tender_data)
