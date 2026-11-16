import time
from Transactions_tests.generate_Auth_req import generate_auth_request_payload
from Transactions_tests.generate_Auth_res import generate_auth_response_payload
from Transactions_tests.generate_order_fulfillment import generate_order_fulfillment_payload
from Transactions_tests.generate_capture_exp import generate_capture_exp_payload
from Transactions_tests.generate_capture_res import generate_capture_res_payload
from utils.Sql_interface import create_sql_connection
from utils.generate_time import utc_now
class TestStepClass:
    def __init__(self, row , merchant , terminal_id , PreviousDispatchPayloads ):
        self.step = row['Step']
        self.DispatchEvent = row['Dispatch T+ seconds']
        self.sourceEvent = row['Logical event T+ seconds']
        self.Event = row['Event / action']
        self.source = row['Source']
        self.status = row['Status / check']
        self.payload = row['Payload JSON']
        
        self.build_test_step(
            previous_payloads=PreviousDispatchPayloads,
            merchant=merchant,
            terminal_id=terminal_id
        )
        
        
    def build_test_step(self , previous_payloads = [] , merchant=None , terminal_id=None):
      cursor = create_sql_connection()
      if self.Event == 'authorization.requested':
        self.payload =  generate_auth_request_payload(self.payload , 
                                             *previous_payloads , 
                                             cursor = cursor 
                                             , merchant = merchant , 
                                             terminal_id = terminal_id)
        previous_payloads.append(self.payload)
      if self.Event == 'authorization.response':
        self.payload = generate_auth_response_payload(self.payload , 
                                              *previous_payloads ,
                                              cursor = cursor , 
                                              merchant = merchant , 
                                              status = self.status,
                                              dispatch_time = float(self.DispatchEvent)
                                              )
        previous_payloads.append(self.payload)
      if self.Event == 'order.fulfillment':
        self.payload = generate_order_fulfillment_payload(self.payload ,
                                                  *previous_payloads ,
                                                  cursor = cursor ,
                                                  merchant = merchant)
        previous_payloads.append(self.payload)
      if self.Event == 'capture.expected':
        self.payload = generate_capture_exp_payload(self.payload ,
                                            *previous_payloads ,
                                            cursor = cursor ,
                                            merchant = merchant,
                                            dispatch_time = float(self.DispatchEvent)
                                            )
        previous_payloads.append(self.payload)
      if self.Event == 'capture.response':
        self.payload = generate_capture_res_payload(self.payload ,
                                            *previous_payloads ,
                                            cursor = cursor ,
                                            merchant = merchant ,
                                            dispatch_time = float(self.DispatchEvent)
                                            )
        previous_payloads.append(self.payload)
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
        self.merchant = merchant
        self.terminal_id = terminal_id
        self.sender = callback_function_sender
        for i in TestSteps:
            if i['Case ID'] == CaseID:
                self.TestSteps.append(TestStepClass(row=i , 
                                                    merchant=merchant , 
                                                    terminal_id=terminal_id , 
                                                    PreviousDispatchPayloads = self.PreviousDispatchPayloads)) 
        
        self.TestSteps.sort(key=lambda obj: 
             (float(obj.DispatchEvent) , int(obj.step)))
       
    def run_test_case(self):
        for i in range(len(self.TestSteps)):
            self.sender(self.TestSteps[i].payload)
            if i+1 == len(self.TestSteps):
                break
            time.sleep(float(self.TestSteps[i+1].DispatchEvent))
            
