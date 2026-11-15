from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Transactions_tests.generate_Auth_req import generate_auth_request_payload
from Transactions_tests.payload_defaults import PayloadDefaults, cached_payload
from utils.generate_random_ids import generate_event_id
from utils.generate_time import utc_now, utc_now_minus_seconds


def generate_order_fulfillment_payload(payload=None, *previous_payloads, cursor=None, merchant=None):
    values = PayloadDefaults(payload, previous_payloads)
    request = cached_payload(lambda: generate_auth_request_payload(None, *previous_payloads, cursor=cursor, merchant=merchant))
    values.add("schema_version", 1)
    values.add("event_id", generate_event_id)
    values.add("event_type", "order.fulfillment")
    values.add("event_time", utc_now)
    values.add("source", "backend")
    for key in ("merchant_id", "payment_id", "order_reference"):
        values.add(key, lambda key=key: request(key), inherit=True)
    values.add("fulfillment_status", "delivered")
    values.add("fulfillment_version", 3)
    values.add("fulfillment_occurred_at", lambda: utc_now_minus_seconds(5))
    return values.to_json()
