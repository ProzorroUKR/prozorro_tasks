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
    """
    scheduled task example
    {'celery@0e5c8165e375': [{'eta': '2019-04-25T10:25:12.021035+00:00', 'priority': 6, 'request': {'id': '6ff8bc3b-fceb-4ae1-9b41-9ff4bd7a26ea', 'name': 'crawler.tasks.echo_task', 'args': '()', 'kwargs': '{}', 'type': 'crawler.tasks.echo_task', 'hostname': 'celery@0e5c8165e375', 'time_start': None, 'acknowledged': False, 'delivery_info': {'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': True}, 'worker_pid': None}}]}
    reserved task example
    {'celery@0e5c8165e375': [{'id': '4436379b-84d5-4089-b88f-c4a83ddcd2d6', 'name': 'crawler.tasks.echo_task', 'args': '(27,)', 'kwargs': '{}', 'type': 'crawler.tasks.echo_task', 'hostname': 'celery@0e5c8165e375', 'time_start': None, 'acknowledged': False, 'delivery_info': {'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': False}, 'worker_pid': None}]}
    active task example
    {'celery@0e5c8165e375': [{'id': '0f84b98b-7b7e-4527-8465-4ad6ba2e2a69', 'name': 'crawler.tasks.spam_task', 'args': '()', 'kwargs': '{}', 'type': 'crawler.tasks.spam_task', 'hostname': 'celery@0e5c8165e375', 'time_start': 1556184976.9029453, 'acknowledged': False, 'delivery_info': {'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': False}, 'worker_pid': 8}]}
    :return:
    """
    # https://github.com/celery/celery/issues/5067
    connection = kombu.Connection(CELERY_BROKER_URL, connect_timeout=5, transport_options=con_opts)
    inspect = app.control.inspect(timeout=1, connection=connection)

    for group in ("scheduled", "active", "reserved"):
        method = getattr(inspect, group)
        response = method() or method()  # sometimes first call returns None
        for worker, tasks in response.items():
            for task in tasks:
                task_info = task.get("request") or task
                if task_info["type"] == task_name:
                    return 0
    return 1


if __name__ == "__main__":
    exit(find_task())
