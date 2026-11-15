from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import random
import json
from utils.generate_random_ids import generate_event_id, generate_capture_id
from utils.generate_time import  utc_now_plus_seconds , utc_now

available_source = ["backend", "webhook"]
def generate_capture_res_payload(payload_auth_res , payload_capture_req):
    Auth_res_payload = json.loads(payload_auth_res)
    Capture_req_payload = json.loads(payload_capture_req)
    source = random.choice(available_source)
    payload = {
       "schema_version": 1,  
       "event_id": generate_event_id(),
       "event_type": "capture.response",
       "event_time":  utc_now_plus_seconds(5),
       "source": source, 
       "capture_id": Capture_req_payload["capture_id"],
       "payment_id": Auth_res_payload["payment_id"],
       "attempt_id": Auth_res_payload["attempt_id"],
       "merchant_id": Auth_res_payload["merchant_id"],
       "order_reference": Auth_res_payload["order_reference"],
       "capture_mode": "automatic",
       "processor": Auth_res_payload["processor"],
       "authorization_reference": Auth_res_payload["processor_reference"],
       "processor_capture_reference": generate_capture_id(),
       "processor_event_time": utc_now(), 
       "status": "succeeded",
       "captured_amount_minor": Auth_res_payload["requested_amount_minor"],
       "currency": Auth_res_payload["currency"],
       "failure": None,
       "retry": None,
    }
    
    damped_payload = json.dumps(payload, indent=4)
    return damped_payload