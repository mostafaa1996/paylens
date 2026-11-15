from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import random
import json
from utils.generate_random_ids import generate_event_id, generate_processor_reference , generate_aurhorization_code
from utils.generate_time import  utc_now_plus_seconds , utc_now

def generate_auth_response_payload(cursor, payload_auth_req , status=None):
    cursor.execute("SELECT processor_code FROM processors")
    processor = cursor.fetchone()
    Auth_req_payload = json.loads(payload_auth_req)
    payload = {
        "schema_version": 1,  
        "event_id": generate_event_id(),
        "event_type": "authorization.response",
        "event_time":  utc_now_plus_seconds(2),
        "source": "webhook",
        "payment_id": Auth_req_payload["payment_id"],
        "attempt_id": Auth_req_payload["attempt_id"],
        "merchant_id": Auth_req_payload["merchant_id"],
        "order_reference": Auth_req_payload["order_reference"],
        "processor": processor.processor_code if processor else None,
        "processor_reference": generate_processor_reference(),
        "processor_event_time": utc_now(), 
        "status": status if status else "authorized",
        "requested_amount_minor": Auth_req_payload["requested_amount_minor"],
        "authorized_amount_minor": Auth_req_payload["requested_amount_minor"] if status == "authorized" else None,
        "currency": Auth_req_payload["currency"],
        "authorization_code": generate_aurhorization_code() if status == "authorized" else None,
        "decline": {
            "provider_code": None,
            "provider_reason": None,
            "reason": None  
        },
        "action": None,
        "error": None
    }
    
    return json.dumps(payload, indent=4)