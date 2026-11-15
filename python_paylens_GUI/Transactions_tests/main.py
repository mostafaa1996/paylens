from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import time
from generate_Auth_req import generate_auth_request_payload
from generate_Auth_res import generate_auth_response_payload
from generate_capture_exp import generate_capture_exp_payload
from select_merchant import select_merchant
from generate_capture_res import generate_capture_res_payload
from generate_order_fulfillment import generate_order_fulfillment_payload
from utils.EventHubs_interface import send_event_hubs_message
from utils.Sql_interface import create_sql_connection
from Transaction_TestCases.TestCasesFromExcelReader import TestCasesFromExcelReader
from Transaction_TestCases.TestCaseClass import TestCaseClass , TestStepClass

# available_status = ["authorized", "declined", "pending", "additional_action" , "error", "timeout", "unknown"]

cursor = create_sql_connection()
merchant = select_merchant(cursor, 21)

# payload_auth_req = generate_auth_request_payload(None, cursor=cursor, merchant=merchant, terminal_id="1234567890", ip_address="192.0.2.10")
# print(payload_auth_req)

# send_event_hubs_message(payload_auth_req)
# time.sleep(3)

# payload_auth_res = generate_auth_response_payload(None, payload_auth_req, cursor=cursor, status="authorized")
# print(payload_auth_res)

# send_event_hubs_message(payload_auth_res)
# time.sleep(3)

# payload_capture_exp = generate_capture_exp_payload(None, payload_auth_res)
# print(payload_capture_exp)

# send_event_hubs_message(payload_capture_exp)
# time.sleep(3)

# payload_order_fulfillment = generate_order_fulfillment_payload(None, payload_auth_res)
# print(payload_order_fulfillment)

# send_event_hubs_message(payload_order_fulfillment)
# time.sleep(5)

# payload_capture_res = generate_capture_res_payload(None, payload_auth_res, payload_capture_exp)
# print(payload_capture_res)

# send_event_hubs_message(payload_capture_res)


reader = TestCasesFromExcelReader(file_path="Transactions_TestCases.xlsx")
reader.read_test_cases()
reader.read_test_steps()

for test_case in reader.TestCases:
    test_case_obj = TestCaseClass(test_case , 
                                  test_case['Case ID'] , 
                                  reader.TestStepsPerTestCase , 
                                  merchant=merchant, 
                                  terminal_id="1234567890",
                                  callback_function_sender=send_event_hubs_message
                                  )
    if test_case_obj.CaseID == "PL-0011":
        test_case_obj.run_test_case()
        print(test_case_obj.CaseID)
        print(test_case_obj.TransactionTestType)
        print(test_case_obj.TransactionDesc)
        print(test_case_obj.TranscationExpectedResult)
        print(test_case_obj.TransactionStepsNumber)
        print(test_case_obj.TestSteps[0].payload)
        print("\n")
        break








