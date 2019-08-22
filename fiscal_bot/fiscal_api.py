from environment_settings import (
    FISCAL_SENDER_NAME, FISCAL_SENDER_STI, FISCAL_SENDER_TIN, FISCAL_BOT_ENV_NUMBER
)
from fiscal_bot.settings import REQUEST_DOC_VERSION
from tasks_utils.datetime import get_now
from celery.utils.log import get_task_logger
from fiscal_bot.utils import get_daily_increment_id, get_monthly_increment_id
import jinja2


logger = get_task_logger(__name__)
TEMPLATES = jinja2.Environment(
    loader=jinja2.PackageLoader('fiscal_bot', 'templates', encoding='windows-1251'),
)


def build_receipt_request(task, tenderID, identifier, name):
    now = get_now()

    c_doc_count = get_monthly_increment_id(task, now.date())
    if len("{:d}".format(c_doc_count)) > 6:
        logger.critical("Month doc count doesn't fit 6 signs")  # I don't really expect this to happen

    filename = "{authority}{identifier}{c_doc}{c_doc_sub}{c_doc_ver:02d}{c_doc_stan}{c_doc_type}" \
               "{env_number:d}{c_doc_count:06d}" \
               "{period_type}{period_month:02d}{period_year}{authority}.xml".format(
                    authority="2659",
                    identifier="0" * (10 - len(FISCAL_SENDER_TIN)) + FISCAL_SENDER_TIN,
                    c_doc="J16",  # J17 for response
                    c_doc_sub="031",
                    c_doc_ver=REQUEST_DOC_VERSION,
                    c_doc_stan="1",
                    c_doc_type="00",
                    env_number=FISCAL_BOT_ENV_NUMBER,
                    c_doc_count=c_doc_count,
                    period_type="1",
                    period_month=now.month,
                    period_year=now.year,
               )
    template = TEMPLATES.get_template('request.xml')

    is_legal = len(identifier) == 8 and identifier.isdigit()
    context = dict(
        sender_tin=FISCAL_SENDER_TIN,
        sender_name=FISCAL_SENDER_NAME,
        sender_sti=FISCAL_SENDER_STI,
        tenderID=tenderID,
        identifier=identifier,
        name=name,
        c_doc_count=c_doc_count,
        h_num=get_daily_increment_id(task, now.date()),
        now=now,
        is_physical=not is_legal,
    )
    if context["is_physical"]:
        name_parts = name.strip().split(" ")
        if len(name_parts) > 0:
            context["last_name"] = name_parts[0]
            if len(name_parts) > 1:
                context["first_name"] = name_parts[1]
                if len(name_parts) > 2:
                    context["patronymic"] = name_parts[2]

    content = template.render(context).encode('windows-1251')

    return filename, content

