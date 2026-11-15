import random
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Transactions_tests.payload_defaults import PayloadDefaults, fill_defaults
from utils.generate_random_ids import generate_event_id, generate_payment_id, generate_attempt_id, generate_order_reference, generate_idempotency_key
from utils.generate_time import utc_now

available_channel = ["web", "mobile", "pos"]


def generate_auth_request_payload(payload=None, *previous_payloads, cursor=None,
                                  merchant=None, terminal_id=None, ip_address="192.0.2.10"):
    """Build a request from a template and earlier payloads (oldest first)."""
    values = PayloadDefaults(payload, previous_payloads)
    values.add("schema_version", 1)
    values.add("event_id", generate_event_id)
    values.add("event_type", "authorization.requested")
    values.add("event_time", utc_now)
    values.add("source", "backend")
    values.add("payment_id", generate_payment_id, inherit=True)
    values.add("attempt_id", generate_attempt_id, inherit=True)
    values.add("merchant_id", lambda: merchant.get("merchant_id") if isinstance(merchant, dict) else getattr(merchant, "merchant_id", None), inherit=True)
    values.add("order_reference", generate_order_reference, inherit=True)
    values.add("requested_amount_minor", lambda: 10000 + random.randint(0, 999999), inherit=True)
    values.add("currency", "EGP", inherit=True)
    channel = values.add("channel", lambda: random.choice(available_channel), inherit=True)

    def payment_token():
        if cursor is None or values.result["merchant_id"] is None:
            return None
        cursor.execute("SELECT * FROM customers where merchant_id = ?", values.result["merchant_id"])
        customers = cursor.fetchall()
        if not customers:
            return None
        customer = random.choice(customers)
        cursor.execute("SELECT payment_token FROM customer_payment_methods where customer_id = ? and is_active = 1", customer.customer_id)
        method = cursor.fetchone()
        return method.payment_token if method else None

    method_defaults = {
        "type": "card",
        "token": payment_token,
        "card_presence": "CNP" if channel in ["web", "mobile"] else "CP",
        "entry_mode": "online" if channel in ["web", "mobile"] else "offline",
    }
    inherited_method = values.previous_value("payment_method") or {}
    method_template = values.template.get("payment_method")
    if method_template is None:
        method_template = inherited_method
    elif isinstance(method_template, dict):
        method_template = fill_defaults(method_template, inherited_method)
    if isinstance(method_template, dict):
        values.result["payment_method"] = fill_defaults(method_template, method_defaults)
    else:
        values.result["payment_method"] = method_template
    values.add("terminal_id", terminal_id if channel == "pos" else None, inherit=True)
    values.add("ip_address", None if channel == "pos" else ip_address, inherit=True)
    values.add("idempotency_key", generate_idempotency_key)
    return values.to_json()
