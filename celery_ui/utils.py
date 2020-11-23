import kombu

from flower.utils.tasks import iter_tasks, get_task_by_id

from celery_worker.celery import app
from environment_settings import CELERY_BROKER_URL


KOMBU_CONNECT_TIMEOUT = 5
KOMBU_TRANSPORT_OPTIONS = {
    "max_retries": 5,
    "interval_start": 1,
    "interval_step": 1,
    "interval_max": 2,
}

DEFAULT_TIMEOUT = 3.0

TASKS_EVENTS_DEFAULT_SORT = "-received"


def kombu_connection():
    # https://github.com/celery/celery/issues/5067
    return kombu.Connection(
        CELERY_BROKER_URL,
        connect_timeout=KOMBU_CONNECT_TIMEOUT,
        transport_options=KOMBU_TRANSPORT_OPTIONS
    )


def inspect_scheduled(task_type=None, timeout=DEFAULT_TIMEOUT):
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
    return inspect_method("scheduled", task_type=task_type, timeout=timeout)

def inspect_active(task_type=None, timeout=DEFAULT_TIMEOUT):
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
    return inspect_method("active", task_type=task_type, timeout=timeout)

def inspect_reserved(task_type=None, timeout=DEFAULT_TIMEOUT):
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
    return inspect_method("reserved", task_type=task_type, timeout=timeout)

def inspect_revoked(task_type=None, timeout=DEFAULT_TIMEOUT):
    """
    :param task_name:
    :param timeout:
    :return: list of tasks data

    revoked task example
        '0f84b98b-7b7e-4527-8465-4ad6ba2e2a69'
    """
    return inspect_method("revoked", task_type=task_type, timeout=timeout)

def inspect_method(method_name, task_type=None, timeout=DEFAULT_TIMEOUT):
    """
    :return:
    """
    connection = kombu_connection()
    inspect = app.control.inspect(
        timeout=timeout,
        connection=connection
    )
    method = getattr(inspect, method_name)
    response = method() or method()  # sometimes first call returns None
    connection.close()
    tasks = list()
    if response:
        for worker, values in response.items():
            for value in values:
                if task_type is not None:
                    task_request = value.get("request", None) or value
                    if task_request["type"] == task_type or task_type is None:
                        value["worker"] = worker
                        tasks.append(value)
                else:
                    value["worker"] = worker
                    tasks.append(value)
    return tasks


def inspect_tasks(task_type=None):
    tasks_list = []
    active = reversed(inspect_active(task_type=task_type))
    for task_inspect_dict in active:
        task_dict = task_inspect_dict
        task_dict["worker"] = task_inspect_dict["worker"]
        task_dict["state"] = "ACTIVE"
        tasks_list.append(task_dict)
    scheduled = reversed(inspect_scheduled(task_type=task_type))
    for task_inspect_dict in scheduled:
        task_dict = task_inspect_dict["request"]
        task_dict["eta"] = task_inspect_dict["eta"]
        task_dict["worker"] = task_inspect_dict["worker"]
        task_dict["state"] = "SCHEDULED"
        tasks_list.append(task_dict)
    reserved = reversed(inspect_reserved(task_type=task_type))
    for task_inspect_dict in reserved:
        task_dict = task_inspect_dict
        task_dict["worker"] = task_inspect_dict["worker"]
        task_dict["state"] = "RESERVED"
        tasks_list.append(task_dict)
    return tasks_list


def revoke_task(uuid, terminate=False):
    app.control.revoke(uuid, terminate=terminate)

def task_as_dict(task):
    task_dict = task.as_dict() if task else {}
    if task_dict.get('worker'):
        task_dict['worker'] = task_dict['worker'].hostname
    return task_dict


def retrieve_task(uuid):
    from celery_ui.events import events
    task_instance = get_task_by_id(events, uuid)
    task_dict = task_as_dict(task_instance)
    return task_dict


def retrieve_tasks(task_type=None, search=None):
    from celery_ui.events import events
    tasks_instances_list = list(iter_tasks(
        events,
        type=task_type,
        search=search,
        sort_by=TASKS_EVENTS_DEFAULT_SORT
    ))
    total = len(tasks_instances_list)
    tasks_list = []
    for task_uuid, task_instance in tasks_instances_list:
        task_dict = task_as_dict(task_instance)
        tasks_list.append(task_dict)
    return tasks_list
