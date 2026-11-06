"""Contract fixtures and local structural checks, not complete JSON Schemas."""
import copy
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from uuid import uuid4

CONTRACTS = json.loads(Path(__file__).with_name("contracts.json").read_text(encoding="utf-8"))
SAMPLES = CONTRACTS["events"]
CSV_SCHEMAS = CONTRACTS["csv"]
EVENT_NAMES = {p["event_type"]: name for name, p in SAMPLES.items()}


def snapshot(value):
    return copy.deepcopy(value)


def new_id(prefix="evt"):
    return f"{prefix}_{uuid4().hex[:12]}"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def body(payload):
    result = payload.get("data", {}) if payload.get("event_type") == "refund.updated" else payload
    return result if isinstance(result, dict) else {}


def family(payload):
    kind = payload.get("event_type", "")
    if not isinstance(kind, str):
        return "Unknown"
    if kind.startswith("authorization"):
        return "Authorization"
    if kind.startswith("capture"):
        return "Capture"
    return "Refund" if kind == "refund.updated" else "Fulfillment" if kind == "order_fulfillment_updated" else "Unknown"


def business_key(payload):
    b = body(payload)
    return str(b.get("payment_id") or f"{b.get('merchant_id', '?')} / {b.get('order_reference', b.get('order_id', '?'))}")


def expected_type(key, sample):
    if key.endswith("_minor") or key in ("schema_version", "refund_version", "fulfillment_version"):
        return str if isinstance(sample, str) else int
    if sample is None:
        return dict if key in ("action", "error") else str
    return type(sample)


def validate(payload, schema=None):
    """Conservative checks of supplied shapes; no invented status enumerations."""
    if not isinstance(payload, dict):
        return ["$: event must be a JSON object"]
    kind = payload.get("event_type")
    name = schema or (EVENT_NAMES.get(kind) if isinstance(kind, str) else None)
    if name not in SAMPLES:
        return ["event_type: choose a supplied schema family"]
    issues = []

    def walk(sample, actual, prefix=""):
        for key, value in sample.items():
            path = f"{prefix}{key}"
            # Null sample values are treated as nullable/omittable assumptions.
            if key not in actual:
                if value is not None:
                    issues.append(f"{path}: missing sample-defined field")
                continue
            got = actual[key]
            if got is None:
                if value is not None:
                    issues.append(f"{path}: null not demonstrated in sample")
                continue
            typ = expected_type(key, value)
            if type(got) is not typ:
                issues.append(f"{path}: expected {typ.__name__}")
                continue
            if isinstance(value, dict):
                walk(value, got, path + ".")
            if key.endswith("_minor") and isinstance(got, int) and got < 0:
                issues.append(f"{path}: negative amount (testing only)")
            if key.endswith("_at") or key.endswith("_time"):
                try:
                    dt = datetime.fromisoformat(got.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        issues.append(f"{path}: timezone required")
                except (ValueError, AttributeError):
                    issues.append(f"{path}: invalid timestamp")
    walk(SAMPLES[name], payload)
    if payload.get("event_type") != SAMPLES[name]["event_type"]:
        issues.append("event_type: differs from selected family")
    if type(payload.get("schema_version")) is not type(SAMPLES[name]["schema_version"]) or payload.get("schema_version") != SAMPLES[name]["schema_version"]:
        issues.append("schema_version: differs from supplied contract")
    if payload.get("capture_mode", "automatic") != "automatic":
        issues.append("capture_mode: automatic capture is the supported scope")
    return issues


def money(value, currency):
    if not isinstance(currency, str):
        return "Currency must be a string for a display conversion"
    digits = {"EGP": 2, "USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3, "BHD": 3}.get(currency)
    if digits is None:
        return "Unknown currency exponent; no conversion assumed"
    if type(value) is not int:
        return "Integer minor units required"
    with localcontext() as context:
        context.prec = max(28, len(str(abs(value))) + 10)
        return f"{currency} {Decimal(value).scaleb(-digits):,.{digits}f} (display only)"


def csv_rows():
    """Small explicit provider-supplied fixtures; money is decimal text."""
    shared = dict(provider_id="provider_demo", provider_account_id="pa_demo", merchant_id="mer_001", currency="EGP", provider_payment_id="ppay_001", provider_capture_id="pcap_001", payout_id="pout_001", entry_id="entry_001", report_id="report_001", updated_at="2026-10-09T10:00:00Z")
    overrides = [
        dict(report_version="1", settlement_batch_id="sb_001", entry_type="SALE", event_time="2026-10-08T09:00:04Z", settlement_date="2026-10-09", record_status="POSTED", gross_amount="1000.00", transaction_currency="EGP", settlement_currency="EGP", fx_rate="1.00000000", gross_settlement_amount="1000.00", fee_amount="20.00", net_amount="980.00"),
        dict(beneficiary_account_id="bankacct_demo", payout_amount="980.00", status="SENT", scheduled_at="2026-10-09T08:00:00Z", sent_at="2026-10-09T10:00:00Z", expected_arrival_date="2026-10-10", bank_transfer_reference="transfer_001"),
        dict(allocation_id="alloc_001", allocated_net_amount="980.00", allocation_source="PROVIDER", created_at="2026-10-09T10:00:00Z"),
        dict(statement_id="stmt_001", bank_id="bank_demo", bank_account_id="bankacct_demo", bank_entry_id="be_001", booking_date="2026-10-10", value_date="2026-10-10", credit_amount="980.00", debit_amount="0.00", transfer_reference="transfer_001", description="Synthetic payout credit", counterparty_name="Demo Provider", balance_after="980.00"),
        dict(payment_id="pay_001", order_id="order_145", capture_attempt_id="ca_001", capture_status="SUCCEEDED", captured_amount="1000.00", captured_at="2026-10-08T09:00:04Z", expected_settlement_date="2026-10-09"),
    ]
    result = {}
    for (name, columns), extra in zip(CSV_SCHEMAS.items(), overrides):
        values = shared | extra
        result[name] = [{key: values.get(key) for key, _ in columns}]
    ledger = result[list(CSV_SCHEMAS)[-1]]
    for state in ("PENDING", "FAILED"):
        row = snapshot(ledger[0])
        row.update(capture_attempt_id=f"ca_{state.lower()}", capture_status=state, captured_amount=None, captured_at=None, provider_capture_id=None, expected_settlement_date=None)
        ledger.append(row)
    return result


def entities(kind):
    if kind == "customers":
        return [dict(customer_id=f"cus_{i:03}", display_name=f"Synthetic Customer {i}", email=f"demo{i}@example.invalid", country="EG", status="active", scenario_tags=[]) for i in range(1, 5)]
    return [dict(merchant_id=f"mer_{i:03}", display_name=f"Demo Merchant {i}", status="active", default_currency="EGP", provider_id="provider_demo", provider_account_id="pa_demo", accounts=[dict(beneficiary_account_id="bankacct_demo", bank_id="bank_demo")]) for i in range(1, 4)]
