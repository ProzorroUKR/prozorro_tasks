import datetime
from dateutil.tz import tzoffset

data_before_parse = b"""
    <root method_name="Obligation">
        <record id="12034">
            <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
            <pmt_status>0</pmt_status>
            <pmt_sum>1161960</pmt_sum>
            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
        </record>
        <record id="12035">
            <pmt_date>2020-05-05T17:46:38+02:00</pmt_date>
            <pmt_status>-1</pmt_status>
            <pmt_sum>1161960</pmt_sum>
            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
        </record>
    </root>
"""

data_before_parse_invalid_field_type = b"""
    <root method_name="Obligation">
        <record id="12034">
            <pmt_date>2020-03-05T17:37:23+02:00</pmt_date>
            <pmt_status>0</pmt_status>
            <pmt_sum>INVALID_NOT_FLOAT</pmt_sum>
            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
        </record>
        <record id="12035">
            <pmt_date>2020-05-05T17:46:38+02:00</pmt_date>
            <pmt_status>-1</pmt_status>
            <pmt_sum>1161960</pmt_sum>
            <contractId>11C2E7D03AF649668BF9FFB1D0EF767D</contractId>
        </record>
    </root>
"""

data_after_parse = [
    {'recordId': 12034,
     'failed_message': [],
     'pmt_date': datetime.datetime(2020, 3, 5, 17, 37, 23, tzinfo=tzoffset(None, 7200)),
     'pmt_status': 0,
     'pmt_sum': 1161960.0,
     'contractId': '11C2E7D03AF649668BF9FFB1D0EF767D'
     },
    {'recordId': 12035,
     'failed_message': [],
     'pmt_date': datetime.datetime(2020, 5, 5, 17, 46, 38, tzinfo=tzoffset(None, 7200)),
     'pmt_status': -1,
     'pmt_sum': 1161960.0,
     'contractId': '11C2E7D03AF649668BF9FFB1D0EF767D'
     }
]

data_after_parse_invalid_field_type = [{
    'recordId': 12034,
    'failed_message': ['pmt_sum has incorrect data type'],
    'pmt_date': datetime.datetime(2020, 3, 5, 17, 37, 23, tzinfo=tzoffset(None, 7200)),
    'pmt_status': 0,
    'contractId': '11C2E7D03AF649668BF9FFB1D0EF767D'
    },
    {
    'recordId': 12035,
    'failed_message': [],
    'pmt_date': datetime.datetime(2020, 5, 5, 17, 46, 38, tzinfo=tzoffset(None, 7200)),
    'pmt_status': -1,
    'pmt_sum': 1161960.0,
    'contractId': '11C2E7D03AF649668BF9FFB1D0EF767D'
 }]

