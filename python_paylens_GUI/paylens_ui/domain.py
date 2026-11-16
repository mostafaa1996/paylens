"""Shared snapshot/time helpers and CSV preview fixtures."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

CSV_SCHEMAS = json.loads(Path(__file__).with_name("contracts.json").read_text(encoding="utf-8"))["csv"]


def snapshot(value):
    return copy.deepcopy(value)


def new_id(prefix="evt"):
    return f"{prefix}_{uuid4().hex[:12]}"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


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
