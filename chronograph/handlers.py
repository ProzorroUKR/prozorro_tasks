from asgiref.sync import sync_to_async

from tasks_utils.datetime import parse_dt_string
from chronograph.tasks import recheck


def chronograph_handler(obj_name):
    async def handler(obj, **kwargs):
        next_check = obj.get('next_check')
        if next_check:
            await sync_to_async(recheck.apply_async)(
                kwargs=dict(
                    obj_name=obj_name,
                    obj_id=obj['id'],
                ),
                eta=parse_dt_string(next_check),
            )
    return handler
