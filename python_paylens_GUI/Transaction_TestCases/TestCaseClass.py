import time
class TestStepClass:
    def __init__(self, row):
        self.step = row['Step']
        self.DispatchEvent = row['Dispatch T+ seconds']
        self.sourceEvent = row['Logical event T+ seconds']
        self.Event = row['Event / action']
        self.source = row['Source']
        self.status = row['Status / check']
        self.payload = row['Payload JSON']

class TestCaseClass:
    def __init__(self, excel_payload , CaseID , TestSteps):
        self.CaseID = excel_payload['Case ID']
        self.TransactionTestType = excel_payload['Transaction journey']
        self.TransactionDesc = excel_payload['Why required']
        self.TranscationExpectedResult = excel_payload['Expected result and reporting purpose']
        self.TransactionStepsNumber = excel_payload['Steps']
        self.TestSteps = []
        self.PreviousDispatchPayload = None
        self.DispatchPayload = None
        for i in TestSteps:
            if i['Case ID'] == CaseID:
                self.TestSteps.append(TestStepClass(i)) 
        
        self.TestSteps.sort(key=lambda obj: 
             (float(obj['Dispatch T+ seconds']) , int(obj['Step'])))
       
    def run_test_case(self):
        for i in range(len(self.TestSteps)):
            self.DispatchPayload = self.TestSteps[i].run_test_step(self.PreviousDispatchPayload)
            if i+1 == len(self.TestSteps):
                break
            self.PreviousDispatchPayload = self.DispatchPayload
            time.sleep(float(self.TestSteps[i+1]['Dispatch T+ seconds']))
            
    def run_test_step(self , previous_payload = None):
        return