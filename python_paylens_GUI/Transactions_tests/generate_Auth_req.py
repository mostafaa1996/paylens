import random
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.generate_random_ids import generate_event_id, generate_payment_id, generate_attempt_id, generate_order_reference, generate_idempotency_key
from utils.generate_time import utc_now

available_channel = ["web", "mobile", "pos"]

def generate_auth_request_payload(cursor, merchant, terminal_id=None, ip_address="192.0.2.10"):
    cursor.execute("SELECT * FROM customers where merchant_id = 21")
    customers = cursor.fetchall()
    random_customer = random.choice(customers)

    cursor.execute("SELECT payment_token FROM customer_payment_methods where customer_id = ? and is_active = 1", random_customer.customer_id)
    payment_method = cursor.fetchone()
    
    channel = random.choice(available_channel)
    card_presence = "CNP" if channel in ["web", "mobile"] else "CP"
    entry_mode = "online" if card_presence == "CNP" else "offline"
    
    payload = {
        "schema_version": 1,
        "event_id": generate_event_id(),
        "event_type": "authorization.requested",
        "event_time": utc_now(),
        "source": "backend",
        "payment_id": generate_payment_id(),
        "attempt_id": generate_attempt_id(),
        "merchant_id": merchant.merchant_id,
        "order_reference": generate_order_reference(),
        "requested_amount_minor": 10000 + random.randint(0, 999999),
        "currency": "EGP",
        "channel": channel,
        "payment_method": {
            "type": "card",
            "token": payment_method.payment_token if payment_method else None,
            "card_presence": card_presence,
            "entry_mode": entry_mode
        },
        "terminal_id": terminal_id if channel == "pos" else None,
        "ip_address": None if channel == "pos" else ip_address,
        "idempotency_key": generate_idempotency_key()
    }

    damped_payload = json.dumps(payload, indent=4)
    return damped_payload





