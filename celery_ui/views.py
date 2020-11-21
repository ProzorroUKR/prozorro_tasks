from ast import literal_eval

from flask import Blueprint, render_template, redirect, url_for, request
from app.auth import login_groups_required
from celery_worker.locks import remove_unique_lock
from celery_ui.utils import (
    revoke_task,
    inspect_active,
    inspect_scheduled,
    inspect_reserved,
    inspect_revoked, inspect_task,
)
from crawler.tasks import process_feed

bp = Blueprint("celery_views", __name__, template_folder="templates")

bp.add_app_template_filter(literal_eval, "literal_eval")

@bp.route("/", methods=["GET"])
@login_groups_required(["admins"])
def celery():
    return redirect(url_for("celery_views.feed"))

@bp.route("/feed", methods=["GET"])
@login_groups_required(["admins"])
def feed():
    task_name = "crawler.tasks.process_feed"

    active=inspect_active(task_name)
    scheduled=inspect_scheduled(task_name)
    reserved=inspect_reserved(task_name)

    def filter_resource(item, resource):
        item_request = item.get("request") or item
        item_kwargs = literal_eval(item_request["kwargs"])
        return item_kwargs["resource"] == resource

    def filtered_resource(resource_name):
        resource = dict()

        active_resource = list(filter(lambda x: filter_resource(x, resource_name), active))
        if active_resource:
            resource["active"] = active_resource

        scheduled_resource = list(filter(lambda x: filter_resource(x, resource_name), scheduled))
        resource["scheduled"] = scheduled_resource

        reserved_resource = list(filter(lambda x: filter_resource(x, resource_name), reserved))
        if reserved_resource:
            resource["reserved"] = reserved_resource

        return resource

    resources = dict(
        tenders=filtered_resource("tenders"),
        contracts=filtered_resource("contracts"),
    )

    return render_template("celery/feed.html", resources=resources)

@bp.route("/tasks", methods=["GET"])
@login_groups_required(["admins"])
def tasks():
    active = inspect_active()
    scheduled = inspect_scheduled()
    reserved = inspect_reserved()
    revoked = inspect_revoked()
    inspect = dict(
        active=active,
        scheduled=scheduled,
        reserved=reserved,
        revoked=revoked,
    )
    return render_template("celery/tasks.html", inspect=inspect)

@bp.route("/tasks/<uuid>", methods=["GET"])
@login_groups_required(["admins"])
def task(uuid):
    inspect = inspect_task(uuid)
    return render_template("celery/task.html", inspect=inspect)

@bp.route("/feed/<resource>/start", methods=["POST"])
@login_groups_required(["admins"])
def feed_start(resource):
    kwargs_str = request.values.get("kwargs")
    kwargs = literal_eval(kwargs_str) if kwargs_str else {}
    kwargs["resource"] = resource
    process_feed.delay(**kwargs)
    return redirect(request.referrer)

@bp.route("/feed/<resource>/unlock", methods=["POST"])
@login_groups_required(["admins"])
def unlock(resource):
    kwargs_str = request.values.get("kwargs")
    kwargs = literal_eval(kwargs_str) if kwargs_str else {}
    kwargs["resource"] = resource
    remove_unique_lock(process_feed)
    return redirect(request.referrer)

@bp.route("/tasks/<uuid>/revoke", methods=["POST"])
@login_groups_required(["admins"])
def revoke(uuid):
    revoke_task(uuid)
    return redirect(request.referrer)
