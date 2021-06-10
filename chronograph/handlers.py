from tasks_utils.datetime import parse_dt_string
from chronograph.tasks import recheck


def chronograph_handler(obj_name):
    def handler(obj, **kwargs):
        next_check = obj.get('next_check')
        if next_check:
            recheck.apply_async(
                kwargs=dict(
                    obj_name=obj_name,
                    obj_id=obj['id'],
                ),
                eta=parse_dt_string(next_check),
            )
    return handler
