import time
from Transactions_tests.generate_Auth_req import generate_auth_request_payload
from Transactions_tests.generate_Auth_res import generate_auth_response_payload
from Transactions_tests.generate_order_fulfillment import generate_order_fulfillment_payload
from Transactions_tests.generate_capture_exp import generate_capture_exp_payload
from Transactions_tests.generate_capture_res import generate_capture_res_payload
from utils.Sql_interface import create_sql_connection
class TestStepClass:
    def __init__(self, row):
        self.step = row['Step']
        self.DispatchEvent = row['Dispatch T+ seconds']
        self.sourceEvent = row['Logical event T+ seconds']
        self.Event = row['Event / action']
        self.source = row['Source']
        self.status = row['Status / check']
        self.payload = row['Payload JSON']
        
    def run_test_step(self , previous_payloads = [] , merchant=None , terminal_id=None):
      cursor = create_sql_connection()
      if self.Event == 'authorization.requested':
        return generate_auth_request_payload(self.payload , 
                                             *previous_payloads , 
                                             cursor = cursor 
                                             , merchant = merchant , 
                                             terminal_id = terminal_id)
      if self.Event == 'authorization.response':
        return generate_auth_response_payload(self.payload , 
                                              *previous_payloads ,
                                              cursor = cursor , 
                                              merchant = merchant , 
                                              status = self.status)
      if self.Event == 'order.fulfillment':
        return generate_order_fulfillment_payload(self.payload ,
                                                  *previous_payloads ,
                                                  cursor = cursor ,
                                                  merchant = merchant)
      if self.Event == 'capture.expected':
        return generate_capture_exp_payload(self.payload ,
                                            *previous_payloads ,
                                            cursor = cursor ,
                                            merchant = merchant)
      if self.Event == 'capture.response':
        return generate_capture_res_payload(self.payload ,
                                            *previous_payloads ,
                                            cursor = cursor ,
                                            merchant = merchant)
class TestCaseClass:
    def __init__(self, 
                 excel_payload , CaseID , 
                 TestSteps , merchant=None , 
                 terminal_id=None , 
                 callback_function_sender=None
                 ):
        self.CaseID = excel_payload['Case ID']
        self.TransactionTestType = excel_payload['Transaction journey']
        self.TransactionDesc = excel_payload['Why required']
        self.TranscationExpectedResult = excel_payload['Expected result and reporting purpose']
        self.TransactionStepsNumber = excel_payload['Steps']
        self.TestSteps = []
        self.PreviousDispatchPayloads = []
        self.DispatchPayload = None
        self.merchant = merchant
        self.terminal_id = terminal_id
        self.sender = callback_function_sender
        for i in TestSteps:
            if i['Case ID'] == CaseID:
                self.TestSteps.append(TestStepClass(i)) 
        
        self.TestSteps.sort(key=lambda obj: 
             (float(obj.DispatchEvent) , int(obj.step)))
       
    def run_test_case(self):
        for i in range(len(self.TestSteps)):
            self.DispatchPayload = self.TestSteps[i].run_test_step(
                 previous_payloads = self.PreviousDispatchPayloads,
                 merchant=self.merchant,
                 terminal_id=self.terminal_id
                )
            self.sender(self.DispatchPayload)
            if i+1 == len(self.TestSteps):
                break
            self.PreviousDispatchPayloads.append(self.DispatchPayload)
            time.sleep(float(self.TestSteps[i+1].DispatchEvent))
            
