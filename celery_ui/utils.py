from celery_worker.celery import app


def inspect_task(uuid):
    return dict(
        id=uuid
    )

def inspect_scheduled(task_name=None):
    return inspect_method("scheduled", task_name=task_name)

def inspect_active(task_name=None):
    return inspect_method("active", task_name=task_name)

def inspect_reserved(task_name=None):
    return inspect_method("reserved", task_name=task_name)

def inspect_revoked(task_name=None):
    return inspect_method("revoked", task_name=task_name)

def inspect_method(method_name, task_name=None):
    inspect = app.control.inspect()
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
