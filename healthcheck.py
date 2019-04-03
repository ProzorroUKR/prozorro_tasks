#!/usr/bin/env python
from environment_settings import CELERY_BROKER_URL
from celery_worker.celery import app
import kombu

con_opts = {
    "max_retries": 5,
    "interval_start": 1,
    "interval_step": 1,
    "interval_max": 2,
}
task_name = "crawler.tasks.process_feed"


def find_task():
    # https://github.com/celery/celery/issues/5067
    connection = kombu.Connection(CELERY_BROKER_URL, connect_timeout=5, transport_options=con_opts)
    inspect = app.control.inspect(timeout=1, connection=connection)

    for group in ("scheduled", "active", "reserved"):
        method = getattr(inspect, group)
        response = method() or method()  # sometimes first call returns None
        for worker, tasks in response.items():
            for task in tasks:
                if task["request"]["type"] == task_name:
                    return 0
    return 1


if __name__ == "__main__":
    exit(find_task())
