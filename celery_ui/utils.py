import kombu

from celery_worker.celery import app
from environment_settings import CELERY_BROKER_URL


KOMBU_TRANSPORT_OPTIONS = {
    "max_retries": 5,
    "interval_start": 1,
    "interval_step": 1,
    "interval_max": 2,
}
KOMBU_CONNECT_TIMEOUT = 5

DEFAULT_TIMEOUT = 3.0


def inspect_task(uuid):
    return dict(
        id=uuid
    )

def inspect_scheduled(task_name=None, timeout=DEFAULT_TIMEOUT):
    """
    :param task_name:
    :param timeout:
    :return: list of tasks data

    scheduled task example
        {
            'celery@0e5c8165e375': [{
                'eta': '2019-04-25T10:25:12.021035+00:00',
                'priority': 6,
                'request': {
                    'id': '6ff8bc3b-fceb-4ae1-9b41-9ff4bd7a26ea', 'name': 'crawler.tasks.echo_task', 'args': '()',
                    'kwargs': '{}', 'type': 'crawler.tasks.echo_task', 'hostname': 'celery@0e5c8165e375',
                    'time_start': None, 'acknowledged': False,
                    'delivery_info': {'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': True},
                    'worker_pid': None
                }
            }]
        }
    """
    return inspect_method("scheduled", task_name=task_name, timeout=timeout)

def inspect_active(task_name=None, timeout=DEFAULT_TIMEOUT):
    """
    :param task_name:
    :param timeout:
    :return: list of tasks data

    reserved task example
        {
            'celery@0e5c8165e375': [{
                'id': '4436379b-84d5-4089-b88f-c4a83ddcd2d6', 'name': 'crawler.tasks.echo_task',
                'args': '(27,)', 'kwargs': '{}', 'type': 'crawler.tasks.echo_task',
                'hostname': 'celery@0e5c8165e375', 'time_start': None, 'acknowledged': False,
                'delivery_info': {
                    'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': False
                }, 'worker_pid': None
            }]
        }
    """
    return inspect_method("active", task_name=task_name, timeout=timeout)

def inspect_reserved(task_name=None, timeout=DEFAULT_TIMEOUT):
    """
    :param task_name:
    :param timeout:
    :return: list of tasks data

    active task example
        {
            'celery@0e5c8165e375': [{
                'id': '0f84b98b-7b7e-4527-8465-4ad6ba2e2a69', 'name': 'crawler.tasks.spam_task',
                'args': '()', 'kwargs': '{}', 'type': 'crawler.tasks.spam_task',
                'hostname': 'celery@0e5c8165e375', 'time_start': 1556184976.9029453,
                'acknowledged': False, 'delivery_info': {
                    'exchange': '', 'routing_key': 'celery', 'priority': 0, 'redelivered': False
                }, 'worker_pid': 8
            }]
        }
    """
    return inspect_method("reserved", task_name=task_name, timeout=timeout)

def inspect_revoked(task_name=None, timeout=DEFAULT_TIMEOUT):
    """
    :param task_name:
    :param timeout:
    :return: list of tasks data

    revoked task example
        '0f84b98b-7b7e-4527-8465-4ad6ba2e2a69'
    """
    return inspect_method("revoked", task_name=task_name, timeout=timeout)

def inspect_method(method_name, task_name=None, timeout=DEFAULT_TIMEOUT):
    """
    :return:
    """
    # https://github.com/celery/celery/issues/5067
    connection = kombu.Connection(
        CELERY_BROKER_URL,
        connect_timeout=KOMBU_CONNECT_TIMEOUT,
        transport_options=KOMBU_TRANSPORT_OPTIONS
    )
    inspect = app.control.inspect(timeout=timeout, connection=connection)
    method = getattr(inspect, method_name)
    response = method() or method()  # sometimes first call returns None
    tasks = list()
    for worker, values in response.items():
        for value in values:
            if task_name is not None:
                task_request = value.get("request", None) or value
                if task_request["type"] == task_name or task_name is None:
                    tasks.append(value)
            else:
                tasks.append(value)
    return tasks

def revoke_task(uuid, terminate=False):
    return app.control.revoke(uuid, terminate=terminate)
