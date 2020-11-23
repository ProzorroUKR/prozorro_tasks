import json
from ast import literal_eval
from datetime import datetime
from pprint import pformat

import dateutil
from flask import Blueprint, render_template, redirect, url_for, request

from app.auth import login_groups_required
from celery_ui.context import get_int_param, get_tasks_pagination
from celery_worker.locks import remove_unique_lock
from celery_ui.utils import (
    revoke_task,
    retrieve_tasks, inspect_tasks, retrieve_task,
)
from crawler.tasks import process_feed, logger
from environment_settings import TIMEZONE

bp = Blueprint("celery_views", __name__, template_folder="templates")

def date_representation(dt):
    if not dt:
        return None
    if type(dt) is str:
        dt = dateutil.parser.parse(dt)
    return dt.astimezone(TIMEZONE).replace(microsecond=0).isoformat(sep=" ")

def timestamp_representation(timestamp):
    if not timestamp:
        return None
    dt = datetime.fromtimestamp(timestamp)
    dt_str = dt.astimezone(TIMEZONE).replace(microsecond=0).isoformat(sep=" ")
    return f"{dt_str} ({timestamp})"

def python_pretty_representation(string):
    try:
        return pformat(literal_eval(string))
    except (ValueError, SyntaxError):
        return string

bp.add_app_template_filter(literal_eval, "literal_eval")
bp.add_app_template_filter(date_representation, "date_representation")
bp.add_app_template_filter(timestamp_representation, "timestamp_representation")
bp.add_app_template_filter(python_pretty_representation, "python_pretty_representation")

TASKS_EVENTS_DEFAULT_PAGE = 1
TASKS_EVENTS_DEFAULT_LIMIT = 10

@bp.route("/", methods=["GET"])
@login_groups_required(["admins"])
def celery():
    return redirect(url_for("celery_views.feeds"))

@bp.route("/feed", methods=["GET"])
@login_groups_required(["admins"])
def feeds():
    task_type = "crawler.tasks.process_feed"
    if bool(get_int_param("inspect", 0)):
        tasks_list = inspect_tasks(task_type=task_type)
    else:
        tasks_list = retrieve_tasks(task_type=task_type)
    resources = {}
    resource_names = ("tenders", "contracts")
    feed_events_states = ('PENDING', 'RECEIVED', 'RETRY', 'STARTED')
    feed_inspect_states = ('ACTIVE', 'SCHEDULED', 'RESERVED')
    for resource_name in resource_names:
        resources[resource_name] = []
    resources["other"] = []
    for task_dict in tasks_list:
        if task_dict["state"] in feed_events_states + feed_inspect_states:
            kwargs_resource = literal_eval(task_dict["kwargs"]).get('resource')
            if kwargs_resource in resource_names:
                resources[kwargs_resource].append(task_dict)
            else:
                resources["other"].append(task_dict)
    return render_template("celery/feed.html", resources=resources)

@bp.route("/feed/<resource>", methods=["GET"])
@login_groups_required(["admins"])
def feed(resource):
    task_type = "crawler.tasks.process_feed"

    if bool(get_int_param("inspect", 0)):
        tasks_list = inspect_tasks(task_type=task_type)
    else:
        tasks_list = retrieve_tasks(task_type=task_type)

    filtered_tasks = []
    for task_dict in tasks_list:
        kwargs_resource = literal_eval(task_dict["kwargs"]).get('resource')
        if kwargs_resource == resource:
            filtered_tasks.append(task_dict)

    if bool(get_int_param("inspect", 0)):
        resources = {resource: filtered_tasks}
        return render_template("celery/feed.html", resources=resources)
    else:
        page = get_int_param("page", TASKS_EVENTS_DEFAULT_PAGE)
        limit = get_int_param("limit", TASKS_EVENTS_DEFAULT_LIMIT)
        start = (page - 1) * limit
        end = start + limit
        resources = {resource: filtered_tasks[start:end]}
        return render_template(
            "celery/feed.html",
            resources=resources,
            pagination = get_tasks_pagination(
                page=page,
                limit=limit,
                total=len(filtered_tasks),
            ),
        )

@bp.route("/tasks", methods=["GET"])
@login_groups_required(["admins"])
def tasks():
    if bool(get_int_param("inspect", 0)):
        tasks_list = inspect_tasks()
        return render_template("celery/tasks.html", tasks=tasks_list)
    else:
        page = get_int_param("page", TASKS_EVENTS_DEFAULT_PAGE)
        limit = get_int_param("limit", TASKS_EVENTS_DEFAULT_LIMIT)
        start = (page - 1) * limit
        end = start + limit
        tasks_list = retrieve_tasks(search=request.args.get("search"))
        return render_template(
            "celery/tasks.html",
            tasks=tasks_list[start:end],
            pagination=get_tasks_pagination(
                page=page,
                limit=limit,
                total=len(tasks_list),
            ),
        )

@bp.route("/tasks/<uuid>", methods=["GET"])
@login_groups_required(["admins"])
def task(uuid):
    task_dict = retrieve_task(uuid)
    return render_template("celery/task.html", data=task_dict)


@bp.route("/feed/<resource>/start", methods=["POST"])
@login_groups_required(["admins"])
def feed_start(resource):
    kwargs_str = request.values.get("kwargs")
    kwargs = literal_eval(kwargs_str) if kwargs_str else {}
    kwargs["resource"] = resource
    process_feed.delay(**kwargs)
    if request.content_type == 'application/json':
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    return redirect(request.referrer)

@bp.route("/feed/<resource>/unlock", methods=["POST"])
@login_groups_required(["admins"])
def feed_unlock(resource):
    kwargs_str = request.values.get("kwargs")
    kwargs = literal_eval(kwargs_str) if kwargs_str else {}
    kwargs["resource"] = resource
    remove_unique_lock(process_feed)
    if request.content_type == 'application/json':
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    return redirect(request.referrer)

@bp.route("/tasks/<uuid>/revoke", methods=["POST"])
@login_groups_required(["admins"])
def revoke(uuid):
    revoke_task(uuid)
    if request.content_type == 'application/json':
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    return redirect(request.referrer)
