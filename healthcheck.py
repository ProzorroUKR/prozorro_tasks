#!/usr/bin/env python
from celery_ui.utils import inspect_scheduled, inspect_active, inspect_reserved

task_name = "crawler.tasks.process_feed"
tasks_count = 2  # we expect to have 2 crawlers: tender and contract


def healthcheck():
    scheduled = inspect_scheduled(task_name, timeout=1)
    active = inspect_active(task_name, timeout=1)
    reserved = inspect_reserved(task_name, timeout=1)
    count = len(scheduled) + len(active) + len(reserved)
    return 1 if count < tasks_count else 0


if __name__ == "__main__":
    exit(healthcheck())
