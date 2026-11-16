from pathlib import Path
import sys
import random

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Transactions_tests.generate_capture_exp import generate_capture_exp_payload
from Transactions_tests.payload_defaults import PayloadDefaults, cached_payload
from utils.generate_random_ids import generate_event_id, generate_capture_id
from utils.generate_time import utc_now_plus_seconds, utc_now

available_source = ["backend", "webhook"]


def generate_capture_res_payload(payload=None, *previous_payloads, cursor=None, merchant=None , dispatch_time=None):
    values = PayloadDefaults(payload, previous_payloads)
    capture = cached_payload(lambda: generate_capture_exp_payload(None, *previous_payloads, cursor=cursor, merchant=merchant))
    values.add("schema_version", 1)
    values.add("event_id", generate_event_id)
    values.add("event_type", "capture.response")
    values.add("event_time", lambda: utc_now_plus_seconds(dispatch_time if dispatch_time is not None else 5), force_default=True)
    values.add("source", lambda: random.choice(available_source))
    for key in ("capture_id", "payment_id", "attempt_id", "merchant_id", "order_reference", "capture_mode", "processor"):
        values.add(key, lambda key=key: capture(key), inherit=True)
    values.add("authorization_reference", lambda: capture("authorization_reference"), inherit=True, aliases=("processor_reference",))
    values.add("processor_capture_reference", generate_capture_id)
    values.add("processor_event_time", lambda: utc_now_plus_seconds(dispatch_time-2 if dispatch_time is not None else 5), force_default=True)
    values.add("status", "succeeded")
    values.add("captured_amount_minor", lambda: capture("expected_amount_minor"), inherit=True, aliases=("expected_amount_minor", "requested_amount_minor"))
    values.add("currency", lambda: capture("currency"), inherit=True)
    values.add("failure")
    values.add("retry")
    return values.to_json()
