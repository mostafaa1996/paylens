from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Transactions_tests.generate_Auth_res import generate_auth_response_payload
from Transactions_tests.payload_defaults import PayloadDefaults, cached_payload
from utils.generate_random_ids import generate_event_id, generate_capture_id
from utils.generate_time import utc_now, utc_now_plus_seconds


def generate_capture_exp_payload(payload=None, *previous_payloads, cursor=None, merchant=None):
    values = PayloadDefaults(payload, previous_payloads)
    authorization = cached_payload(lambda: generate_auth_response_payload(None, *previous_payloads, cursor=cursor, merchant=merchant))
    values.add("schema_version", 1)
    values.add("event_id", generate_event_id)
    values.add("event_type", "capture.expected")
    values.add("event_time", utc_now)
    values.add("source", "backend")
    values.add("capture_id", generate_capture_id, inherit=True)
    for key in ("payment_id", "attempt_id", "merchant_id", "order_reference"):
        values.add(key, lambda key=key: authorization(key), inherit=True)
    values.add("capture_mode", "automatic", inherit=True)
    values.add("processor", lambda: authorization("processor"), inherit=True)
    values.add("authorization_reference", lambda: authorization("processor_reference"), inherit=True, aliases=("processor_reference",))
    values.add("expected_amount_minor", lambda: authorization("requested_amount_minor"), inherit=True, aliases=("requested_amount_minor",))
    values.add("currency", lambda: authorization("currency"), inherit=True)
    values.add("expected_capture_at", lambda: utc_now_plus_seconds(60))
    values.add("follow_up_at", lambda: utc_now_plus_seconds(180))
    return values.to_json()
