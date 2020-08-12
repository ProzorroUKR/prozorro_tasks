from treasury.tasks import (
    check_contract, send_contract_xml, send_change_xml, request_org_catalog,
    receive_org_catalog, send_transactions_results, process_transaction
)
from celery.exceptions import Retry
from unittest.mock import patch, Mock, call
from datetime import datetime
import unittest
from treasury.settings import (
    PUT_TRANSACTION_SUCCESSFUL_STATUS,
    ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS,
)


@patch('celery_worker.locks.get_mongodb_collection',
       Mock(return_value=Mock(find_one=Mock(return_value=None))))
class CheckTestCase(unittest.TestCase):

    @patch("treasury.tasks.sign_data")
    @patch("treasury.tasks.get_now")
    @patch("treasury.tasks.uuid4")
    @patch("treasury.tasks.receive_org_catalog")
    @patch("treasury.tasks.render_catalog_xml")
    @patch("treasury.tasks.send_request")
    def test_get_org_catalog(self, send_request_mock, render_xml_mock, receive_catalog_mock, uuid4_mock,
                             get_now_mock, sign_data_mock):
        sign_data_mock.return_value = b"<signature>"
        get_now_mock.return_value = datetime(2007, 1, 1)
        render_xml_mock.return_value = b"<request>da</request>"

        request_org_catalog()

        render_xml_mock.assert_called_once_with(dict(catalog_id="RefOrgs"))
        message_id = uuid4_mock().hex
        send_request_mock.assert_called_once_with(
            request_org_catalog,
            render_xml_mock.return_value,
            sign=sign_data_mock.return_value,
            message_id=message_id,
            method_name="GetRef",
        )
        receive_catalog_mock.apply_async.assert_called_once_with(
            eta=datetime(2007, 1, 1, 0, 3),  # +3 min
            kwargs=dict(
                message_id=message_id,
            )
        )

    @patch("treasury.tasks.update_organisations")
    @patch("treasury.tasks.parse_organisations")
    @patch("treasury.tasks.get_request_response")
    def test_response_org_catalog(self, get_response_mock, parse_org_mock, update_org_mock):
        message_id = "214"
        get_response_mock.return_value = b"resp data"
        parse_org_mock.return_value = b"org1, org2"

        receive_org_catalog(message_id)

        get_response_mock.assert_called_once_with(
            receive_org_catalog,
            message_id=message_id
        )
        parse_org_mock.assert_called_once_with(
            get_response_mock.return_value
        )
        update_org_mock.assert_called_once_with(
            receive_org_catalog,
            parse_org_mock.return_value
        )

    @patch("treasury.tasks.get_request_response")
    def test_response_org_catalog_empty(self, get_response_mock):
        message_id = "214"
        get_response_mock.return_value = None

        with self.assertRaises(Retry):
            receive_org_catalog(message_id)

    @patch("treasury.tasks.send_contract_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_first_stage_tender")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract(self, get_data_mock, get_first_stage_tender_mock, get_org_mock, get_context_mock,
                            prepare_context_mock, save_context_mock, send_contract_xml_mock):
        contract_id = "4444"
        get_org_mock.return_value = {"org data"}
        contract_data = dict(
            id=contract_id,
            status="active",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        first_stage_tender_id = "23456789"
        tender_data_second_stage = dict(
            id="1234",
            procurementMethodType="competitiveDialogueEU.stage2",
            dialogueID=first_stage_tender_id
        )
        tender_data_first_stage = dict(
            id=first_stage_tender_id,
            procurementMethodType="competitiveDialogueEU",
            plans=[dict(id="321")]
        )
        get_first_stage_tender_mock.return_value = tender_data_first_stage
        plan_data = dict(id="321")
        get_data_mock.side_effect = [
            contract_data,
            tender_data_first_stage,
            plan_data
        ]
        get_context_mock.return_value = None
        prepare_context_mock.return_value = {"iam": "context"}

        # run
        check_contract(contract_id)

        # checks
        get_org_mock.assert_called_once_with(check_contract, contract_data["procuringEntity"]["identifier"]["id"])
        get_context_mock.assert_called_once_with(
            check_contract,
            contract_id
        )
        self.assertEqual(
            get_data_mock.mock_calls,
            [
                call(check_contract, contract_id, "contract"),
                call(check_contract, contract_data["tender_id"], "tender"),
                call(check_contract, tender_data_first_stage["plans"][0]["id"], "plan")
            ]
        )
        prepare_context_mock.assert_called_once_with(
            check_contract, contract_data, tender_data_first_stage, plan_data
        )
        save_context_mock.assert_called_once_with(
            check_contract,
            contract_id,
            prepare_context_mock.return_value
        )
        send_contract_xml_mock.delay.assert_called_once_with(contract_id)

    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_ignore_date_signed(self, get_data_mock, get_org_mock):

        contract_id = 123456
        procuring_entity_id = 1234

        contract_data = dict(
            id=contract_id,
            dateSigned="2020-05-20T13:49:00+02:00",
            status="active",
            procuringEntity=dict(
                identifier=dict(
                    id=procuring_entity_id,
                    scheme="UA-EDR"
                )
            )
        )
        get_data_mock.return_value = contract_data
        get_org_mock.return_value = None

        # run
        with patch("treasury.tasks.TREASURY_INT_START_DATE", "2020-08-25"):
            check_contract(contract_id, ignore_date_signed=True)

        # checks
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_called_once_with(check_contract, procuring_entity_id)

    @patch("treasury.tasks.send_contract_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_first_stage_tender")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_without_plan(self, get_data_mock, get_first_stage_tender_mock, get_org_mock,
                                         get_context_mock, prepare_context_mock,
                                         save_context_mock, send_contract_xml_mock):
        contract_id = "4444"
        get_org_mock.return_value = {"org data"}
        contract_data = dict(
            id=contract_id,
            status="active",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        first_stage_tender_id = "23456789"
        tender_data_second_stage = dict(
            id="1234",
            procurementMethodType="competitiveDialogueEU.stage2",
            dialogueID=first_stage_tender_id
        )
        tender_data = dict(
            id=first_stage_tender_id,
            procurementMethodType="competitiveDialogueEU"
        )
        get_first_stage_tender_mock.return_value = tender_data

        get_data_mock.side_effect = [
            contract_data,
            tender_data,
        ]
        get_context_mock.return_value = None
        prepare_context_mock.return_value = {"iam": "context"}

        # run
        check_contract(contract_id)

        # checks
        get_org_mock.assert_called_once_with(check_contract, contract_data["procuringEntity"]["identifier"]["id"])
        get_context_mock.assert_called_once_with(
            check_contract,
            contract_id
        )
        self.assertEqual(
            get_data_mock.mock_calls,
            [
                call(check_contract, contract_id, "contract"),
                call(check_contract, contract_data["tender_id"], "tender"),
            ]
        )
        prepare_context_mock.assert_called_once_with(
            check_contract, contract_data, tender_data, None
        )
        save_context_mock.assert_called_once_with(
            check_contract,
            contract_id,
            prepare_context_mock.return_value
        )
        send_contract_xml_mock.delay.assert_called_once_with(contract_id)

    @patch("treasury.tasks.send_contract_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_before_start(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
                                         save_context_mock, send_contract_xml_mock):
        contract_id = "4444"
        contract_data = dict(
            id=contract_id,
            dateSigned="2020-03-11T13:49:00+02:00",
        )
        get_data_mock.return_value = contract_data

        # run
        with patch("treasury.tasks.TREASURY_INT_START_DATE", "2020-03-12"):
            check_contract(contract_id)

        # checks
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_not_called()
        get_context_mock.assert_not_called()
        prepare_context_mock.assert_not_called()
        save_context_mock.assert_not_called()
        send_contract_xml_mock.delay.assert_not_called()

    @patch("treasury.tasks.send_contract_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_inactive(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
                                     save_context_mock, send_contract_xml_mock):
        contract_id = "4444"
        contract_data = dict(
            id=contract_id,
            status="cancelled",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        get_data_mock.return_value = contract_data

        # run
        check_contract(contract_id)

        # checks
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_not_called()
        get_context_mock.assert_not_called()
        prepare_context_mock.assert_not_called()
        save_context_mock.assert_not_called()
        send_contract_xml_mock.delay.assert_not_called()

    @patch("treasury.tasks.send_contract_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_org_not_found(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
                                          save_context_mock, send_contract_xml_mock):
        contract_id = "4444"
        get_org_mock.return_value = None
        contract_data = dict(
            id=contract_id,
            status="active",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        get_data_mock.return_value = contract_data

        # run
        check_contract(contract_id)

        # checks
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_called_once_with(check_contract, contract_data["procuringEntity"]["identifier"]["id"])
        get_context_mock.assert_not_called()
        prepare_context_mock.assert_not_called()
        save_context_mock.assert_not_called()
        send_contract_xml_mock.delay.assert_not_called()

    @patch("treasury.tasks.send_change_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_contract_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_update(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
                                   save_context_mock, send_change_xml_mock):
        contract_id = "4444"
        get_org_mock.return_value = {"org data"}
        contract_data = dict(
            id=contract_id,
            status="active",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            changes=[
                dict(id="222"),
                dict(id="333"),
            ],
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        get_data_mock.return_value = contract_data
        get_context_mock.return_value = dict(contract=dict(changes=[
            dict(id="111")
        ]))
        prepare_context_mock.return_value = {"iam": "context"}

        # run
        check_contract(contract_id)

        # checks
        get_context_mock.assert_called_once_with(
            check_contract,
            contract_id
        )
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_called_once_with(check_contract, contract_data["procuringEntity"]["identifier"]["id"])
        prepare_context_mock.assert_called_once_with(contract_data)
        save_context_mock.assert_called_once_with(
            check_contract,
            contract_id,
            {"contract": contract_data}
        )
        self.assertEqual(
            send_change_xml_mock.delay.mock_calls,
            [
                call(contract_id, contract_data["changes"][0]["id"]),
                call(contract_id, contract_data["changes"][1]["id"]),
            ]
        )

    @patch("treasury.tasks.send_change_xml")
    @patch("treasury.tasks.save_contract_context")
    @patch("treasury.tasks.prepare_contract_context")
    @patch("treasury.tasks.get_contract_context")
    @patch("treasury.tasks.get_organisation")
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract_no_updates(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
                                       save_context_mock, send_change_xml_mock):
        contract_id = "4444"
        get_org_mock.return_value = {"org data"}
        contract_data = dict(
            id=contract_id,
            status="active",
            tender_id="1234",
            dateSigned="2021-03-11T13:49:00+02:00",
            changes=[
                dict(id="111"),
                dict(id="222"),
            ],
            procuringEntity=dict(
                identifier=dict(
                    id="12345678",
                    scheme="UA-EDR"
                )
            )
        )
        get_data_mock.return_value = contract_data
        get_context_mock.return_value = dict(contract=dict(changes=[
            dict(id="111"),
            dict(id="222"),
        ]))

        # run
        check_contract(contract_id)

        # checks
        get_context_mock.assert_called_once_with(
            check_contract,
            contract_id
        )
        get_data_mock.assert_called_once_with(check_contract, contract_id, "contract")
        get_org_mock.assert_called_once_with(check_contract, contract_data["procuringEntity"]["identifier"]["id"])
        prepare_context_mock.assert_not_called()
        save_context_mock.assert_not_called()
        send_change_xml_mock.assert_not_called()

    @patch("treasury.tasks.sign_data")
    @patch("treasury.tasks.send_request")
    @patch("treasury.tasks.uuid4")
    @patch("treasury.tasks.render_contract_xml")
    @patch("treasury.tasks.prepare_documents")
    @patch("treasury.tasks.get_contract_context")
    def test_send_contract_xml(self, get_context_mock, prepare_documents_mock, render_xml_mock,
                               uuid4_mock, send_mock, sign_data_mock):
        context = dict(
            contract=dict(
                changes=[
                    dict(id="111"),
                    dict(id="222"),
                ]
            )
        )
        get_context_mock.return_value = context
        render_xml_mock.return_value = b"<hello/>"
        message_id = "123abc"
        uuid4_mock.return_value = Mock(hex=message_id)
        sign_data_mock.return_value = b"<signature>"
        contract_id = "55555"

        send_contract_xml(contract_id)

        get_context_mock.assert_called_once_with(
            send_contract_xml,
            contract_id
        )
        self.assertEqual(
            prepare_documents_mock.mock_calls,
            [
                call(send_contract_xml, context["contract"]),
                call(send_contract_xml, context["contract"]["changes"][0]),
                call(send_contract_xml, context["contract"]["changes"][1])
            ]
        )
        render_xml_mock.assert_called_once_with(context)
        sign_data_mock.assert_called_once_with(send_contract_xml, render_xml_mock.return_value)
        send_mock.assert_called_once_with(
            send_contract_xml,
            render_xml_mock.return_value,
            sign=sign_data_mock.return_value,
            message_id=message_id,
            method_name="PrContract"
        )

    @patch("treasury.tasks.sign_data")
    @patch("treasury.tasks.send_request")
    @patch("treasury.tasks.uuid4")
    @patch("treasury.tasks.render_change_xml")
    @patch("treasury.tasks.prepare_documents")
    @patch("treasury.tasks.get_contract_context")
    def test_send_change_xml(self, get_context_mock, prepare_documents_mock, render_xml_mock,
                             uuid4_mock, send_mock, sign_data_mock):
        context = dict(
            contract=dict(
                changes=[
                    dict(id="111"),
                    dict(id="222"),
                ]
            )
        )
        get_context_mock.return_value = context
        render_xml_mock.return_value = b"<hello/>"
        message_id = "123abc"
        uuid4_mock.return_value = Mock(hex=message_id)
        sign_data_mock.return_value = b"<signature>"
        contract_id = "55555"

        send_change_xml(contract_id, "222")

        get_context_mock.assert_called_once_with(
            send_change_xml,
            contract_id
        )
        prepare_documents_mock.assert_called_once_with(
            send_change_xml,
            context["contract"]["changes"][1]
        )
        render_xml_mock.assert_called_once_with(context)
        send_mock.assert_called_once_with(
            send_change_xml,
            render_xml_mock.return_value,
            sign=sign_data_mock.return_value,
            message_id=message_id,
            method_name="PrChange"
        )

    @patch("treasury.tasks.send_request")
    @patch("treasury.tasks.render_change_xml")
    @patch("treasury.tasks.prepare_documents")
    @patch("treasury.tasks.get_contract_context")
    def test_send_unknown_change_xml(self, get_context_mock, prepare_documents_mock, render_xml_mock, send_mock):
        context = dict(
            contract=dict(
                changes=[
                    dict(id="111"),
                    dict(id="222"),
                ]
            )
        )
        get_context_mock.return_value = context
        render_xml_mock.return_value = b"<hello/>"
        contract_id = "55555"

        send_change_xml(contract_id, "333")

        get_context_mock.assert_called_once_with(
            send_change_xml,
            contract_id
        )
        prepare_documents_mock.assert_not_called()
        render_xml_mock.assert_not_called()
        send_mock.assert_not_called()

    @patch("treasury.tasks.send_transactions_results")
    @patch("treasury.tasks.save_transaction_xml")
    @patch("treasury.tasks.put_transaction")
    @patch("treasury.tasks.attach_doc_to_contract")
    def test_process_transaction(self, attach_doc_mock, put_mock, save_xml_mock, send_results_mock):
        transactions_data = [
            {
                "ref": 123,
                "id_contract": 900000
            },
            {
                "ref": 456,
                "id_contract": 800000
            },
            {
                "ref": 789,
                "id_contract": 900000
            }
        ]
        source = "test_source"
        message_id = 'test_message_id_123'

        save_xml_mock.return_value = {
            "data": "test_save_xml_data"
        }
        put_mock.side_effect = [
            (PUT_TRANSACTION_SUCCESSFUL_STATUS, 'cookies'),
            (PUT_TRANSACTION_SUCCESSFUL_STATUS, 'cookies'),
            (404, 'cookies'),
        ]
        attach_doc_mock.side_effect = [ATTACH_DOCUMENT_TO_TRANSACTION_SUCCESSFUL_STATUS, 400]

        process_transaction(transactions_data, source, message_id)
        send_results_mock.delay.assert_called_once_with(
            [True, False, False],
            transactions_data,
            message_id
        )

    @patch("treasury.tasks.render_transactions_confirmation_xml")
    @patch("treasury.tasks.get_now")
    @patch("treasury.tasks.sign_data")
    @patch("treasury.tasks.send_request")
    def test_send_transactions_results(
            self, send_request_mock, sign_mock, get_now_mock, mock_xml
    ):

        get_now_mock.return_value = datetime(2015, 2, 3)

        with open("treasury/tests/fixtures/transactions_confirmation.xml", "rb") as f:
            confirmation_data = f.read()

        mock_xml.return_value = confirmation_data
        sign_mock.return_value = '12345sign'

        transactions_statuses = [False, True, True]

        transactions_data = [
            {
                'ref': 123,
                'id_contract': 345,
                'doc_sq': 400
            },
            {
                'ref': 345,
                'id_contract': 567,
                'doc_sq': 500
            },
            {
                'ref': 789,
                'id_contract': 345,
                'doc_sq': 300
            }
        ]

        message_id = '123456_message'

        send_transactions_results(transactions_statuses, transactions_data, message_id)

        mock_xml.assert_called_once_with(
            date='2015-02-03T00:00:00', rec_count='2', reg_sum='1200', register_id=message_id, status_id='1'
        )

        # send_request_mock.assert_called_once_with(
        #     confirmation_data, '12345sign', message_id, method_name='ConfirmPRTrans')

        mock_xml.reset_mock()
        transactions_statuses = [True, True, True]
        send_transactions_results(transactions_statuses, transactions_data, message_id)

        mock_xml.assert_called_once_with(
            date='2015-02-03T00:00:00', rec_count='3', reg_sum='1200', register_id=message_id, status_id='0'
        )

        mock_xml.reset_mock()
        transactions_statuses = [400, 400, 400]
        send_transactions_results(transactions_statuses, transactions_data, message_id)

        mock_xml.assert_called_once_with(
            date='2015-02-03T00:00:00', rec_count='0', reg_sum='1200', register_id=message_id, status_id='-1'
        )
