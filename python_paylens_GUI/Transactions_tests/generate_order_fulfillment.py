from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import random
import json
from utils.generate_random_ids import generate_event_id
from utils.generate_time import  utc_now , utc_now_minus_seconds

def generate_order_fulfillment_payload(payload_auth_res):
    Auth_res_payload = json.loads(payload_auth_res)
    payload = {
        "schema_version": 1,  
        "event_id": generate_event_id(),
        "event_type": "order.fulfillment",
        "event_time":  utc_now(),
        "source": "backend",
        "merchant_id": Auth_res_payload["merchant_id"],
        "payment_id": Auth_res_payload["payment_id"],
        "order_reference": Auth_res_payload["order_reference"],
        "fulfillment_status": "delivered",
        "fulfillment_version": 3,
        "fulfillment_occurred_at": utc_now_minus_seconds(5),
    }
    
    return json.dumps(payload, indent=4)