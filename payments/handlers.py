from payments.tasks import process_tender


def payments_tender_handler(tender):
    process_tender.delay(tender_id=tender['id'])
