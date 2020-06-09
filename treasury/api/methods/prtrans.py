from treasury.api.parsers.prtrans import TransFields
from treasury.api.builders import XMLResponse
from treasury.tasks import save_transaction


class PRTrans:

    def __init__(self, data, message_id):
        xml_pr_trans_data_parser = TransFields(data)
        self.fields = xml_pr_trans_data_parser.parse()
        self.message_id = message_id

    def run(self):
        fields = self.fields
        save_transaction.delay(
            source=self.fields.data.decode(errors="ignore"),
            transaction=dict(
                contract_id=fields.id_contract,
                transaction_id=fields.ref,
                data=dict(
                    date=fields.msrprd_date,
                    value=dict(
                        amount=fields.doc_sq,
                        currency="UAH"
                    ),
                    payer=dict(
                        id=fields.doc_iban_a,
                        name=fields.doc_nam_a,
                    ),
                    payee=dict(
                        id=fields.doc_iban_b,
                        name=fields.doc_nam_b,
                    ),
                    status=fields.doc_status
                )
            )
        )
        return XMLResponse(code="0", message="Sent to processing")
