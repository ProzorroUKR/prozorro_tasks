from treasury.tasks import check_contract, send_contract_xml, send_change_xml, request_org_catalog, receive_org_catalog, save_transaction, put_transaction
from environment_settings import API_HOST, API_VERSION, API_TOKEN
from celery.exceptions import Retry
from requests.exceptions import ConnectionError
from unittest.mock import patch, Mock, call
from datetime import datetime
import unittest


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
    @patch("treasury.tasks.get_public_api_data")
    def test_check_contract(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
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
        tender_data = dict(
            id="1234",
            plans=[dict(id="321")]
        )
        plan_data = dict(id="321")
        get_data_mock.side_effect = [
            contract_data,
            tender_data,
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
                call(check_contract, tender_data["plans"][0]["id"], "plan")
            ]
        )
        prepare_context_mock.assert_called_once_with(
            check_contract, contract_data, tender_data, plan_data
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
    def test_check_contract_without_plan(self, get_data_mock, get_org_mock, get_context_mock, prepare_context_mock,
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
        tender_data = dict(id="1234")
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


class TransactionsCheckTestCase(unittest.TestCase):

    @patch("treasury.tasks.ds_upload")
    @patch("treasury.tasks.put_transaction")
    def test_save_transaction(self, put_transaction_mock, ds_upload_mock):
        ds_upload_mock.return_value = {
            "url": "http://whatever",
        }
        source = b"abc"
        transaction = dict(
            transaction_id="1234",
            data=dict(
                status=-1,
                something="test 1 2",
            ))

        save_transaction(source, transaction)

        ds_upload_mock.assert_called_once_with(
            save_transaction,
            file_content=b'abc',
            file_name='Transaction_1234_-1.xml'
        )
        put_transaction_mock.delay.assert_called_once_with(
            data={
                'status': -1,
                'something': "test 1 2",
                'documents': [
                    {
                        'url': ds_upload_mock.return_value["url"],
                        'documentType': 'dataSource'
                    }
                ]
            },
            transaction_id='1234'
        )

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction(self, session_mock):
        session_mock.return_value.head.return_value = Mock(
            status_code=404,
        )
        session_mock.return_value.put.return_value = Mock(
            status_code=201,
        )
        contract_id = "12345"
        transaction_id = "567"
        data = {
            "a": "b",
            "documents": [
                {"url": "http://example"}
            ]
        }

        # run
        put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once_with(
            f'{API_HOST}/api/{API_VERSION}/contract/{contract_id}/transactions/{transaction_id}',
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            timeout=(5.0, 30.0)
        )
        session_mock.return_value.put.assert_called_once_with(
            f'{API_HOST}/api/{API_VERSION}/contract/{contract_id}/transactions/{transaction_id}',
            json={'data': {
                'a': 'b',
                'documents': [{'url': 'http://example'}]
            }},
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            timeout=(5.0, 30.0)
        )
        session_mock.return_value.patch.assert_not_called()

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction_patch(self, session_mock):
        session_mock.return_value.head.return_value = Mock(
            status_code=200,
            json=lambda: {
                "data": {
                    "documents": [
                        {}, {}
                    ]
                }
            }
        )
        session_mock.return_value.patch.return_value = Mock(
            status_code=200,
        )
        contract_id = "12345"
        transaction_id = "567"
        data = {
            "a": "b",
            "documents": [
                {"url": "http://example"}
            ]
        }

        # run
        put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once()
        session_mock.return_value.patch.assert_called_once_with(
            f'{API_HOST}/api/{API_VERSION}/contract/{contract_id}/transactions/{transaction_id}',
            json={
                'data': {
                    'a': 'b',
                    'documents': [{}, {}, {'url': 'http://example'}]
                }
            },
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            timeout=(5.0, 30.0)
        )
        session_mock.return_value.put.assert_not_called()

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction_head_exc(self, session_mock):
        session_mock.return_value.head.side_effect = ConnectionError()
        contract_id = "12345"
        transaction_id = "567"
        data = {
            "a": "b",
            "documents": [
                {"url": "http://example"}
            ]
        }

        # run
        with patch("treasury.tasks.put_transaction.retry", Retry):
            with self.assertRaises(Retry):
                put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once()
        session_mock.return_value.patch.assert_not_called()
        session_mock.return_value.put.assert_not_called()

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction_put_exc(self, session_mock):
        session_mock.return_value.head.return_value = Mock(status_code=404)
        session_mock.return_value.put.side_effect = ConnectionError()
        contract_id = "12345"
        transaction_id = "567"
        data = {}

        class RetryExc(Exception):
            def __init__(self, **_):
                pass

        # run
        with patch("treasury.tasks.put_transaction.retry", RetryExc):
            with self.assertRaises(RetryExc):
                put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once()
        session_mock.return_value.patch.assert_not_called()
        session_mock.return_value.put.assert_called_once()

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction_retry(self, session_mock):
        session_mock.return_value.head.return_value = Mock(status_code=404)
        session_mock.return_value.put.return_value = Mock(status_code=500)
        contract_id = "12345"
        transaction_id = "567"
        data = {}

        class RetryExc(Exception):
            def __init__(self, **_):
                pass

        # run
        with patch("treasury.tasks.put_transaction.retry", RetryExc):
            with self.assertRaises(RetryExc):
                put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once()
        session_mock.return_value.patch.assert_not_called()
        session_mock.return_value.put.assert_called_once()

    @patch("treasury.tasks.requests.Session")
    def test_put_transaction_error_code(self, session_mock):
        session_mock.return_value.head.return_value = Mock(status_code=404)
        session_mock.return_value.put.return_value = Mock(status_code=422)
        contract_id = "12345"
        transaction_id = "567"
        data = {}

        # run
        put_transaction(contract_id, transaction_id, data)

        # checks
        session_mock.return_value.head.assert_called_once()
        session_mock.return_value.patch.assert_not_called()
        session_mock.return_value.put.assert_called_once()
