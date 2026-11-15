from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import json
from utils.generate_random_ids import generate_event_id, generate_capture_id
from utils.generate_time import  utc_now , utc_now_plus_seconds


def generate_capture_exp_payload(payload_auth_res):
    Auth_res_payload = json.loads(payload_auth_res)
    payload = {
        "schema_version": 1,  
        "event_id": generate_event_id(),
        "event_type": "capture.expected",
        "event_time":  utc_now(),
        "source": "backend",
        "capture_id": generate_capture_id(),
        "payment_id": Auth_res_payload["payment_id"],
        "attempt_id": Auth_res_payload["attempt_id"],
        "merchant_id": Auth_res_payload["merchant_id"],
        "order_reference": Auth_res_payload["order_reference"],
        "capture_mode": "automatic",
        "processor": Auth_res_payload["processor"],
        "authorization_reference": Auth_res_payload["processor_reference"],
        "expected_amount_minor": Auth_res_payload["requested_amount_minor"],
        "currency": Auth_res_payload["currency"],
        "expected_capture_at": utc_now_plus_seconds(60),
        "follow_up_at": utc_now_plus_seconds(180)
    }
    return json.dumps(payload , indent=4)