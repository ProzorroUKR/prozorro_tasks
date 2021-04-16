import pymongo
from datetime import datetime, timedelta, date
from celery.utils.log import get_task_logger
from pymongo import ASCENDING, DESCENDING
from pytz import UTC

from celery_worker.locks import args_to_uid, get_mongodb_collection as base_get_mongodb_collection
from functools import partial
from pymongo.errors import PyMongoError, OperationFailure, DuplicateKeyError

from environment_settings import TIMEZONE
from app.logging import log_exc
from payments.data import PAYMENTS_FAILED_MESSAGE_ID_LIST, PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST
from payments.utils import filter_payment_data

logger = get_task_logger(__name__)

get_mongodb_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_results"
)

get_mongodb_status_collection = partial(
    base_get_mongodb_collection,
    collection_name="payments_status"
)

UID_KEYS_1 = [
    "description",
    "amount",
    "currency",
    "date_oper",
    "type",
    "account",
    "okpo",
    "mfo",
    "name",
]

UID_KEYS_2 = UID_KEYS_1 + [
    "source",
]

UID_KEYS_3 = UID_KEYS_2 + [
    "odb_ref",
]


def init_indexes():
    collection = get_mongodb_collection()
    drop_indexes(collection)
    indexes = [
        dict(keys="createdAt", name="created_at"),
        dict(keys=[("payment.description", pymongo.TEXT)], name="payment_description_text"),
    ]
    for kwargs in indexes:
        try:
            init_index(collection, **kwargs)
        except OperationFailure:
            # Index already exists
            pass

    status_collection = get_mongodb_status_collection()
    try:
        init_index(status_collection, keys="createdAt", expireAfterSeconds=24 * 3600 * 30)
    except OperationFailure:
        # Index already exists
        pass


@log_exc(logger, PyMongoError, "MONGODB_INDEX_DROP_UNEXPECTED_ERROR")
def drop_indexes(collection):
    collection.drop_indexes()


@log_exc(logger, PyMongoError, "MONGODB_INDEX_CREATION_UNEXPECTED_ERROR")
@log_exc(logger, OperationFailure, "MONGODB_INDEX_CREATION_ERROR")
def init_index(collection, **kwargs):
    collection.create_index(**kwargs)


def data_to_uid(data, keys=None):
    return args_to_uid(sorted([
        str(value) if not isinstance(value, dict) else data_to_uid(value)
        for key, value in data.items()
        if keys is None or key in keys
    ]))


def query_payment_find(data):
    return {
        "$or": [
            {
                "$and": [
                    {"payment.odb_ref": {"$exists": True}},
                    {"payment.odb_ref": data.get("odb_ref")},
                ]
            },
            {
                "$and": [
                    {"payment.odb_ref": {"$exists": False}},
                    {
                        "$or": [
                            {"_id": data_to_uid(data, keys=UID_KEYS_3)},
                            {"_id": data_to_uid(data, keys=UID_KEYS_2)},
                            {"_id": data_to_uid(data, keys=UID_KEYS_1)},
                        ]
                    },
                ]
            },
        ]
    }


def pipeline_payments_count(field):
    return [
        {
            "$group": {
                "_id": field,
                "count": {'$sum': 1}
            }
        },
        {
            "$group": {
                "_id": None,
                "counts": {'$push': {"k": {"$ifNull": ["$_id", "null"]}, "v": "$count"}},
            }
        },
        {
            "$replaceRoot": {
                "newRoot": {"$arrayToObject": "$counts"}
            }
        }
    ]


def pipeline_payments_counts_date(field, date_wrapper=lambda x: x):
    return [
        {
            "$group": {
                "_id": date_wrapper(field),
                "count": {'$sum': 1}
            }
        },
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"_id": ASCENDING}},
        {
            "$group": {
                "_id": None,
                "counts": {'$push': {"k": "$_id", "v": "$count"}},
            }
        },
        {"$replaceRoot": {"newRoot": {"$arrayToObject": "$counts"}}},
    ]


def pipeline_payments_counts_total():
    return [
        {
            "$group": {
                "_id": None,
                "total": {'$sum': 1}
            },
        },
        {
            "$project": {
                "_id": 0,
            }
        },
    ]


def pipeline_payments_results(page=None, limit=None):
    return [
        {
            "$group": {
                "_id": None,
                "results": {'$push': '$$ROOT'}
            }
        },
        {
            "$project": {
                "results": {
                    "$slice": ["$results", page * limit - limit, limit]
                } if page and limit else "$results",
            }
        },
        {"$unwind": "$results"},
        {"$replaceRoot": {"newRoot": "$results"}}
    ]


def project_payments_results_counts_total():
    return {
        "$arrayElemAt": [{
            "$cond": {
                "if": {"$eq": [{"$size": "$counts_total"}, 0]},
                "then": [{"total": 0}],
                "else": "$counts_total"
            }
        }, 0]
    }


def project_payments_results_counts(field):
    return {"$arrayElemAt": [field, 0]}


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION")
def get_payment_results(filters=None, page=None, limit=None, **kwargs):
    collection = get_mongodb_collection()
    pipeline = [
        {"$match": filters},
        {"$sort": {"createdAt": DESCENDING}},
        {
            "$facet": {
                "results": pipeline_payments_results(page, limit),
                "counts_total": pipeline_payments_counts_total(),
            }
        },
        {
            "$project": {
                "results": 1,
                "meta": {
                    "$mergeObjects": [
                        project_payments_results_counts_total(),
                        {
                            "page": page,
                            "limit": limit,
                        }
                    ]
                }
            }
        }
    ]
    cursor = collection.aggregate(pipeline)
    return list(cursor)[0]


def query_date_split(field):
    return {"$arrayElemAt": [{"$split": [field, "T"]}, 0]}


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_MONGODB_EXCEPTION")
def get_payment_stats(filters=None, page=None, limit=None, **kwargs):
    collection = get_mongodb_collection()
    pipeline = [
        {"$match": filters},
        {"$sort": {"createdAt": DESCENDING}},
        {
            "$facet": {
                "counts_type": pipeline_payments_count('$payment.type'),
                "counts_source": pipeline_payments_count('$payment.source'),
                "counts_date_oper": pipeline_payments_counts_date(
                    "$payment.date_oper",
                    lambda x: query_date_to_str(query_date_from_str(x))
                ),
                "counts_date_resolution": pipeline_payments_counts_date(
                    "$resolution.date",
                    lambda x: query_date_split(x)
                ),
            }
        },
        {
            "$project": {
                "counts_date_resolution": 1,
                "counts": {
                    "type": project_payments_results_counts("$counts_type"),
                    "source": project_payments_results_counts("$counts_source"),
                    "date_oper": project_payments_results_counts("$counts_date_oper"),
                    "date_resolution": project_payments_results_counts("$counts_date_resolution")
                },
            }
        }
    ]
    cursor = collection.aggregate(pipeline)
    return list(cursor)[0]


@log_exc(logger, PyMongoError, "PAYMENTS_PUSH_MESSAGE_MONGODB_EXCEPTION")
def push_payment_message(data, message_id, message):
    collection = get_mongodb_collection()
    query = query_payment_find(data)
    update = {
        "$push": {
            "messages": {
                "message_id": message_id,
                "message": message,
                "createdAt": datetime.utcnow()
            }
        }
    }
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_COUNT_MONGODB_EXCEPTION")
def find_payment_item(data, **kwargs):
    collection = get_mongodb_collection()
    query = query_payment_find(data)
    return collection.find_one(query)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_RESULTS_ITEM_MONGODB_EXCEPTION")
def get_payment_item(uid):
    collection = get_mongodb_collection()
    query = {"_id": uid}
    return collection.find_one(query)


@log_exc(logger, PyMongoError, "PAYMENTS_SAVE_RESULTS_MONGODB_EXCEPTION")
def save_payment_item(data, user):
    status = data.get("status")
    if status and status not in ["success", "failure"]:
        return
    collection = get_mongodb_collection()
    uid = data_to_uid(data, keys=UID_KEYS_3)
    document = {
        "_id": uid,
        "payment": filter_payment_data(data),
        "user": user,
        "createdAt": datetime.utcnow(),
    }
    try:
        return collection.insert_one(document)
    except DuplicateKeyError:
        pass


@log_exc(logger, PyMongoError, "PAYMENTS_UPDATE_RESULTS_MONGODB_EXCEPTION")
def update_payment_item(uid, data):
    collection = get_mongodb_collection()
    query = {
        "_id": uid,
    }
    update = {
        "$set": {
            "payment": filter_payment_data(data),
            "updatedAt": datetime.utcnow(),
        }
    }
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_SET_PARAMS_MONGODB_EXCEPTION")
def set_payment_params(data, params):
    collection = get_mongodb_collection()
    query = query_payment_find(data)
    update = {"$set": {"params": params}}
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_SET_AUTHOR_MONGODB_EXCEPTION")
def set_payment_complaint_author(data, author):
    collection = get_mongodb_collection()
    query = query_payment_find(data)
    update = {"$set": {"author": author}}
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_SET_RESOLUTION_MONGODB_EXCEPTION")
def set_payment_resolution(data, resolution):
    collection = get_mongodb_collection()
    query = query_payment_find(data)
    update = {"$set": {"resolution": resolution}}
    return collection.update_one(query, update)


@log_exc(logger, PyMongoError, "PAYMENTS_GET_BY_PARAMS_MONGODB_EXCEPTION")
def get_payment_item_by_params(params, message_ids=None):
    collection = get_mongodb_collection()
    filters = []
    for param_key, param_value in params.items():
        filters.append({"params.{}".format(param_key): param_value})
    if message_ids:
        filters.append({"messages.message_id": {"$in": message_ids}})
    return collection.find_one(query_combined_and(filters))


def query_payment_search(
    search=None,
    payment_type=None,
    payment_source=None,
    payment_date_from=None,
    payment_date_to=None,
    **kwargs
):
    filters = []
    if search is not None:
        filters.append({"$text": {"$search": search}})
    if payment_type is not None:
        filters.append({"payment.type": payment_type})
    if payment_source is not None:
        filters.append({"payment.source": payment_source})
    if payment_date_from is not None and payment_date_to is not None:
        filters.append({
            "$expr": {
                "$and": [
                    {"$gte": [query_date_from_str("$payment.date_oper"), payment_date_from]},
                    {"$lt": [query_date_from_str("$payment.date_oper"), payment_date_to + timedelta(days=1)]}
                ]
            }
        })
    return query_combined_and(filters) if filters else {}


def query_payment_report_success(
    resolution_exists=None,
    resolution_date_from=None,
    resolution_date_to=None,
    resolution_funds=None,
    **kwargs
):
    filters = []
    if resolution_exists is not None:
        filters.append({"resolution": {"$exists": resolution_exists}})
    if resolution_funds is not None:
        filters.append({"resolution.funds": resolution_funds})
    if resolution_date_from is not None and resolution_date_to is not None:
        filters.append({
            "resolution.date": {
                "$gte": resolution_date_from.isoformat(),
                "$lt": resolution_date_to.isoformat()
            }
        })
    return query_combined_and(filters) if filters else {}


def query_payment_report_failed(
    message_ids_include=None,
    message_ids_date_from=None,
    message_ids_date_to=None,
    message_ids_exclude=None,
    **kwargs
):
    filters = []
    if message_ids_include is not None:
        filters.append({"messages.message_id": {"$in": message_ids_include}})
    messages_match_filter = {}
    if message_ids_include is not None:
        messages_match_filter.update({"message_id": {"$in": message_ids_include}})
    if message_ids_date_from is not None and message_ids_date_to is not None:
        message_ids_date_from = UTC.normalize(TIMEZONE.localize(message_ids_date_from))
        message_ids_date_to = UTC.normalize(TIMEZONE.localize(message_ids_date_to))
        messages_match_filter.update({
            "createdAt": {
                "$gte": message_ids_date_from,
                "$lt": message_ids_date_to
            }
        })
    filters.append({"messages": {"$elemMatch": messages_match_filter}})
    if message_ids_exclude is not None:
        filters.append({"messages.message_id": {"$not": {"$in": message_ids_exclude}}})
    return query_combined_and(filters) if filters else {}


def query_combined_and(filters):
    return {"$and": filters}


def query_combined_or(filters):
    return {"$or": filters}


def query_date_from_str(field, format="%d.%m.%Y %H:%M:%S"):
    return {
        "$dateFromString": {
            "dateString": field,
            "format": format,
            "onError": None
        }
    }


def query_date_to_str(date, format="%Y-%m-%d"):
    return {
        "$dateToString": {
            "date": date,
            "format": format,
            "onNull": None
        }
    }


@log_exc(logger, PyMongoError, "PAYMENTS_STATUS_LIST_MONGODB_EXCEPTION")
def get_statuses_list(limit=None):
    collection = get_mongodb_status_collection()
    cursor = collection.find().sort("createdAt", DESCENDING)
    if limit:
        cursor = cursor.limit(limit)
    return cursor


@log_exc(logger, PyMongoError, "PAYMENTS_STATUS_SAVE_MONGODB_EXCEPTION")
def save_status(data):
    collection = get_mongodb_status_collection()
    try:
        insert_data = {
            "_id": data_to_uid(data),
            "data": data.copy(),
            "createdAt": datetime.utcnow(),
        }
        collection.insert(insert_data)
        return insert_data
    except DuplicateKeyError:
        pass


def query_payment_results(date_from, date_to, **search_kwargs):
    search_filters = query_payment_search(**search_kwargs)
    data_success_filters = query_payment_report_success(
        resolution_date_from=date_from,
        resolution_date_to=date_to,
    )
    data_failed_filters = query_payment_report_failed(
        message_ids_include=PAYMENTS_FAILED_MESSAGE_ID_LIST,
        message_ids_exclude=PAYMENTS_NOT_FAILED_MESSAGE_ID_LIST,
        message_ids_date_from=date_from,
        message_ids_date_to=date_to,
    )
    report_filters = query_combined_or([data_success_filters, data_failed_filters])
    filters = query_combined_and([search_filters, report_filters])
    return filters
