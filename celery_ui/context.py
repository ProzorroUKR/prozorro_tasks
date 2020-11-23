from flask import request
from flask_paginate import Pagination


def get_int_param(name, default=None):
    try:
        param = int(request.args.get(name, default))
    except ValueError:
        param = default
    return param

def get_tasks_pagination(total=None, page=None, limit=None, **kwargs):
    return Pagination(
        bs_version=4,
        link_size="sm",
        show_single_page=True,
        record_name="payments",
        per_page_parameter="limit",
        page_parameter="page",
        total=total,
        page=page,
        limit=limit,
        **kwargs
    )
