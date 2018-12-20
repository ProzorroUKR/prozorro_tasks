from celery_worker.celery import app


def dummy_handler_1(item):
    print("Dummy #1> {} {}".format(item["tenderID"], item["dateModified"]))


@app.task
def dummy_handler_2_task(item):
    print("Dummy #2> {} {}".format(item["tenderID"], item["dateModified"]))


def dummy_handler_2(item):
    dummy_handler_2_task.delay(item)
