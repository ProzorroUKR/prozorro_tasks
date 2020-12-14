from tasks_utils.datetime import parse_dt_string
from chronograph.tasks import recheck_framework


def chronograph_framework_handler(framework, **kwargs):
    next_check = framework.get('next_check')
    if next_check:
        recheck_framework.apply_async(
            kwargs=dict(
                framework_id=framework['id'],
            ),
            eta=parse_dt_string(next_check),
        )
