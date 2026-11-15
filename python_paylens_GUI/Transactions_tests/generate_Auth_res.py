from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Transactions_tests.generate_Auth_req import generate_auth_request_payload
from Transactions_tests.payload_defaults import PayloadDefaults, cached_payload
from utils.generate_random_ids import generate_event_id, generate_processor_reference, generate_aurhorization_code
from utils.generate_time import utc_now_plus_seconds, utc_now


def generate_auth_response_payload(payload=None, *previous_payloads, cursor=None, merchant=None, status=None):
    values = PayloadDefaults(payload, previous_payloads)
    request = cached_payload(lambda: generate_auth_request_payload(None, *previous_payloads, cursor=cursor, merchant=merchant))
    values.add("schema_version", 1)
    values.add("event_id", generate_event_id)
    values.add("event_type", "authorization.response")
    values.add("event_time", lambda: utc_now_plus_seconds(2))
    values.add("source", "webhook")
    for key in ("payment_id", "attempt_id", "merchant_id", "order_reference"):
        values.add(key, lambda key=key: request(key), inherit=True)

    def processor_code():
        if cursor is None:
            return None
        cursor.execute("SELECT processor_code FROM processors")
        processor = cursor.fetchone()
        return processor.processor_code if processor else None

    values.add("processor", processor_code, inherit=True)
    values.add("processor_reference", generate_processor_reference)
    values.add("processor_event_time", utc_now)
    resolved_status = values.add("status", status if status is not None else "authorized")
    amount = values.add("requested_amount_minor", lambda: request("requested_amount_minor"), inherit=True)
    values.add("authorized_amount_minor", amount if resolved_status == "authorized" else None)
    values.add("currency", lambda: request("currency"), inherit=True)
    values.add("authorization_code", lambda: generate_aurhorization_code() if resolved_status == "authorized" else None)
    values.add("decline", {"provider_code": None, "provider_reason": None, "reason": None})
    values.add("action")
    values.add("error")
    return values.to_json()
