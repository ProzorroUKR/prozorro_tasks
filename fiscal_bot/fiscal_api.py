from environment_settings import (
    FISCAL_SENDER_NAME, FISCAL_SENDER_STI, FISCAL_SENDER_TIN
)
from tasks_utils.datetime import get_now
from fiscal_bot.utils import get_increment_id
import jinja2


TEMPLATES = jinja2.Environment(
    loader=jinja2.PackageLoader('fiscal_bot', 'templates', encoding='windows-1251'),
)


def build_receipt_request(task, tenderID, identifier, name):
    now = get_now()

    c_doc_count = get_increment_id(task, now.date())
    filename = "{authority}{identifier}{c_doc}{c_doc_sub}{c_doc_ver}{c_doc_stan}{c_doc_type}{c_doc_count:07d}" \
               "{period_type}{period_month:02d}{period_year}{authority}.xml".format(
                    authority="2659",
                    identifier="0" * (10 - len(identifier)) + identifier,
                    c_doc="J16",  # J17 for response
                    c_doc_sub="031",
                    c_doc_ver="01",
                    c_doc_stan="1",
                    c_doc_type="00",
                    c_doc_count=c_doc_count,
                    period_type="1",
                    period_month=now.month,
                    period_year=now.year,
               )

    template = TEMPLATES.get_template('request.xml')

    context = dict(
        sender_tin=FISCAL_SENDER_TIN,
        sender_name=FISCAL_SENDER_NAME,
        sender_sti=FISCAL_SENDER_STI,
        tenderID=tenderID,
        identifier=identifier,
        name=name,
        c_doc_count=c_doc_count,
        now=now,
        is_physical=len(identifier) == 8 and identifier[2:].isdigit() or len(identifier) == 10 and identifier.isdigit(),
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

