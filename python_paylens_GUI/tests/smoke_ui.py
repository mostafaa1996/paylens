"""Offline UI checks. Run from the repository root; screenshots are opt-in."""
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from paylens_ui.domain import SAMPLES, CSV_SCHEMAS, snapshot, validate, money, family, body
from paylens_ui.widgets import PayloadForm
from paylens_ui.window import MainWindow

app = QApplication.instance() or QApplication([])


def pump_until(predicate, seconds=4):
    deadline = time.monotonic() + seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
    assert predicate(), "Timed out waiting for mock adapter"


class UiSmoke(unittest.TestCase):
    def setUp(self):
        self.window = MainWindow()
        self.window.show()
        app.processEvents()

    def tearDown(self):
        self.window.hide()
        self.window.deleteLater()
        app.processEvents()

    def test_exact_samples_and_nested_editors(self):
        for name, sample in SAMPLES.items():
            with self.subTest(name=name):
                self.assertEqual(validate(sample, name), [])
                form = PayloadForm(sample, sample)
                payload, errors = form.payload()
                self.assertEqual(errors, [])
                self.assertEqual(payload, sample)
                self.assertEqual(type(payload["schema_version"]), type(sample["schema_version"]))
                self.assertIn(("data", "refund_amount_minor") if name == "Refund" else ("event_id",), form.fields)
                form.deleteLater()
        c = self.window.composer
        for schema, path, value in [("Authorization Request", ("payment_method", "entry_mode"), "test"),
                                    ("Authorization Response", ("decline", "reason"), "test_reason"),
                                    ("Capture Result", ("retry", "state"), "test_state"),
                                    ("Refund", ("data", "provider_status"), "test_status")]:
            c.schema.setCurrentText(schema)
            c.form.fields[path].editor.setText(value)
            p = c.drafts[schema]
            for key in path:
                p = p[key]
            self.assertEqual(p, value)

    def test_raw_roundtrip_unknown_fields_and_invalid_known_types(self):
        c = self.window.composer
        p = snapshot(SAMPLES["Authorization Request"])
        p["extra"] = {"zero": 0, "empty": "", "false": False, "null": None}
        p["payment_method"]["custom"] = [1, False, None]
        p["payment_id"] = ["deliberate wrong type"]
        c.raw.setChecked(True)
        c.preview.set_payload(p)
        self.assertTrue(c.apply_raw())
        c.raw.setChecked(False)
        c.form.fields[("currency",)].editor.setText("JPY")
        self.assertEqual(c.drafts[c.current_name]["extra"], p["extra"])
        self.assertEqual(c.drafts[c.current_name]["payment_id"], p["payment_id"])
        self.assertEqual(c.drafts[c.current_name]["payment_method"]["custom"], [1, False, None])
        self.assertTrue(validate(c.drafts[c.current_name]))
        c.raw.setChecked(True)
        c.preview.setPlainText('{broken')
        self.assertFalse(c.apply_raw())
        self.assertTrue(c.raw_pending)

    def test_null_omitted_empty_large_zero_false_and_time(self):
        c = self.window.composer
        amount = c.form.fields[("requested_amount_minor",)]
        self.assertIn("EGP 1,000.00", amount.equivalent.text())
        amount.editor.setText("99999999999999")
        self.assertEqual(c.drafts[c.current_name]["requested_amount_minor"], 99999999999999)
        amount.editor.setText("0")
        self.assertEqual(c.drafts[c.current_name]["requested_amount_minor"], 0)
        terminal = c.form.fields[("terminal_id",)]
        terminal.state.setCurrentText("Value")
        terminal.editor.setText("")
        self.assertEqual(c.drafts[c.current_name]["terminal_id"], "")
        terminal.state.setCurrentText("Null")
        self.assertIsNone(c.drafts[c.current_name]["terminal_id"])
        terminal.state.setCurrentText("Omitted")
        self.assertNotIn("terminal_id", c.drafts[c.current_name])
        c.schema.setCurrentText("Capture Result")
        c.form.fields[("failure", "retryable")].editor.setCurrentText("false")
        self.assertIs(c.drafts[c.current_name]["failure"]["retryable"], False)
        c.form.fields[("provider_event_time",)].editor.setText("2026-10-08T12:00:00+03:00")
        self.assertEqual(c.drafts[c.current_name]["provider_event_time"], "2026-10-08T12:00:00+03:00")
        self.assertEqual(money(100000, "EGP"), "EGP 1,000.00 (display only)")
        self.assertEqual(money(100000, "JPY"), "JPY 100,000 (display only)")
        self.assertIn("Unknown", money(100000, "ZZZ"))
        self.assertIn("must be a string", money(100000, ["malformed_currency"]))
        self.assertIn("999,999,999,999,999,999,999,999,999,999.99", money(99999999999999999999999999999999, "EGP"))

    def fill_stack(self):
        for name, payload in SAMPLES.items():
            self.window.add_to_stack(payload, dict(schema=name, scenario="UI smoke fixture", testing=False))

    def test_mixed_stack_clone_duplicate_reorder_and_snapshot_isolation(self):
        self.fill_stack()
        w = self.window
        self.assertEqual(len(w.stack.items), 6)
        original = snapshot(w.stack.items[0]["payload"])
        w.composer.form.fields[("payment_id",)].editor.setText("pay_changed")
        self.assertEqual(w.stack.items[0]["payload"], original)
        w.stack.table.selectRow(0)
        w.stack.duplicate(True)
        clone = w.stack.items[-1]
        self.assertNotEqual(clone["payload"]["event_id"], original["event_id"])
        self.assertEqual(clone["payload"]["attempt_id"], original["attempt_id"])
        w.stack.table.selectRow(0)
        w.stack.duplicate(False)
        self.assertEqual(w.stack.items[-1]["payload"], original)
        self.assertTrue(w.stack.items[-1]["testing"])
        w.stack.table.selectRow(0)
        w.stack.move(1)
        self.assertEqual(w.stack.items[1]["payload"], original)
        self.assertEqual(w.history.records[0]["payload"], original)
        w.stack.items[1]["payload"]["event_id"] = "changed_later"
        self.assertEqual(w.history.records[0]["payload"], original)

    def test_async_partial_dispatch_cancel_and_exact_resend(self):
        self.fill_stack()
        w = self.window
        w.stack.items[1]["simulate_failure"] = True
        items = snapshot(w.stack.items)
        w.start_dispatch(items, dict(delay_ms=0, stop_on_error=True))
        pump_until(lambda: not w.adapter.running)
        self.assertEqual([r["outcome"] for r in w.adapter.results], ["accepted", "failed"])
        self.assertEqual(sum(r["state"] == "cancelled" for r in w.stack.items), 4)
        self.assertEqual(len(w.history.records), 8)
        prior = snapshot(w.history.records[-1])
        retry = snapshot(items[1]); retry["simulate_failure"] = False
        w.start_dispatch([retry], dict(delay_ms=0))
        pump_until(lambda: not w.adapter.running)
        latest = w.history.records[-1]
        self.assertEqual(latest["payload"], prior["payload"])
        self.assertNotEqual(latest["attempt_id"], prior["attempt_id"])
        w.start_dispatch(items, dict(arrival_delay_ms=5000))
        w.adapter.cancel()
        self.assertFalse(w.adapter.running)
        self.assertEqual(w.adapter.results, [])

    def test_testing_confirmation_strict_block_and_real_not_implemented(self):
        w = self.window
        p = snapshot(SAMPLES["Authorization Request"])
        p["requested_amount_minor"] = "malformed"
        item = dict(payload=p, schema="Authorization Request", scenario="malformed", token="x", testing=False)
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.Ok) as warning:
            w.start_dispatch([item], {})
            warning.assert_called_once()
            self.assertFalse(w.adapter.running)
        item["testing"] = True
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question:
            w.start_dispatch([item], {})
            question.assert_called_once()
            self.assertFalse(w.adapter.running)
        w.settings.adapter.setCurrentIndex(1)
        w.start_dispatch([item], {})
        self.assertIn("Not implemented", w.feedback_label.text())
        self.assertFalse(w.adapter.running)

    def test_history_linking_search_and_save_states(self):
        w = self.window
        w.history.demo()
        self.assertEqual(len(w.history.records), 6)
        self.assertEqual([family(r["payload"]) for r in w.history.records], ["Authorization", "Authorization", "Capture", "Capture", "Fulfillment", "Refund"])
        w.history.search.setText("pay_9001")
        self.assertEqual(len(w.history.model.records), 1)
        w.history.table.selectRow(0)
        self.assertIn("pay_9001", w.history.timeline.toPlainText())
        w.history.save_failure()
        self.assertEqual(w.history.records[-1]["save_state"], "SIMULATED save failed")
        self.assertEqual(w.history.records[-1]["outcome"], "prepared")
        w.history.search.setText("order_145")
        self.assertEqual(len(w.history.model.records), 5)
        self.assertNotIn("payment_id", SAMPLES["Order Fulfillment"])
        w.settings.autosave.setChecked(True)
        calls = []
        w.hooks.request_save_history.connect(lambda p, m: calls.append((p, m)))
        w.history.record(dict(payload=SAMPLES["Refund"], schema="Refund", scenario="prepared"))
        self.assertEqual(calls, [])
        w.history.record(dict(payload=SAMPLES["Refund"], schema="Refund", scenario="dispatch", outcome="accepted"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(w.history.records[-1]["save_state"], "pending integration")

    def test_csv_contracts_editing_and_relations(self):
        w = self.window
        tabs = w.batch.datasets
        for tab, (name, columns) in zip(tabs, CSV_SCHEMAS.items()):
            self.assertEqual(tab.name, name)
            self.assertEqual([c[1] for c in tab.model.columns], [key for key, _ in columns])
        settlement, payout, allocation, bank, ledger = [t.model.records[0] for t in tabs]
        self.assertEqual(settlement["entry_id"], allocation["entry_id"])
        self.assertEqual(ledger["provider_capture_id"], settlement["provider_capture_id"])
        self.assertEqual(payout["payout_id"], allocation["payout_id"])
        self.assertEqual(payout["beneficiary_account_id"], bank["bank_account_id"])
        self.assertEqual(payout["payout_amount"], bank["credit_amount"])
        self.assertEqual({r["capture_status"] for r in tabs[-1].model.records}, {"SUCCEEDED", "PENDING", "FAILED"})
        tabs[0].model.setData(tabs[0].model.index(0, 0), "manually_modified")
        self.assertIn(0, tabs[0].model.modified)
        self.assertEqual(tabs[0].model.records[0]["report_id"], "manually_modified")
        tabs[0].exception_enabled.setChecked(True)
        tabs[0].preset.setCurrentText("Missing column")
        tabs[0].apply_exception()
        self.assertEqual(len(tabs[0].model.columns), 21)
        tabs[0].restore()
        self.assertEqual(len(tabs[0].model.columns), 22)
        w.batch.allocations.setChecked(False)
        tabs[2].restore()
        self.assertEqual(tabs[2].model.records, [])
        w.batch.allocations.setChecked(True)
        self.assertEqual(len(w.batch.config(True)["files"]), 5)

    def test_external_merchant_ids_and_navigation(self):
        w = self.window
        self.assertEqual([b.text() for b in w.nav.buttons()],
                         ["Event Composer", "Event Stack", "Batch Files", "Event History", "Settings"])
        self.assertEqual(w.pages.count(), 5)
        for name in ("customers", "merchants"):
            self.assertFalse(hasattr(w, name))
            self.assertFalse(hasattr(w.hooks, f"request_generate_{name}"))
        for name, sample in SAMPLES.items():
            with self.subTest(name=name):
                w.composer.schema.setCurrentText(name)
                path = ("data", "merchant_id") if name == "Refund" else ("merchant_id",)
                w.composer.form.fields[path].editor.setText("merchant_from_sql")
                payload = w.composer.drafts[name]
                self.assertEqual(body(payload)["merchant_id"], "merchant_from_sql")
                self.assertNotIn("customer_id", body(payload))
                self.assertEqual(validate(payload, name), [])
                w.add_to_stack(payload, dict(schema=name, scenario="Existing SQL merchant", testing=False))
                self.assertEqual(w.stack.items[-1]["payload"], payload)
                self.assertEqual(w.history.records[-1]["payload"], payload)
                self.assertNotEqual(body(sample)["merchant_id"], "merchant_from_sql")

    def test_resolutions_and_all_pages(self):
        w = self.window
        for width, height in ((1280, 800), (1440, 900), (1920, 1080)):
            w.resize(width, height)
            app.processEvents()
            self.assertEqual(w.size().toTuple(), (width, height))
            for index in range(w.pages.count()):
                w.navigate(index)
                app.processEvents()
                page = w.pages.currentWidget()
                self.assertLessEqual(page.minimumSizeHint().width(), page.width())
                self.assertLessEqual(page.minimumSizeHint().height(), page.height())
        w.navigate(0)
        self.assertTrue(w.composer.add_button.isVisible())


def screenshots():
    window = MainWindow()
    window.show()
    for name, payload in SAMPLES.items():
        window.add_to_stack(payload, dict(schema=name, scenario="Exact supplied sample • independent fixture", testing=False))
    window.stack.table.selectRow(0)
    window.history.table.selectRow(0)
    destination = ROOT / "screenshots"
    destination.mkdir(exist_ok=True)
    for width, height in ((1280, 800), (1440, 900), (1920, 1080)):
        window.resize(width, height)
        for index, name in enumerate(("composer", "stack", "batch", "history", "settings")):
            window.navigate(index)
            app.processEvents()
            if width == 1440 or index in (0, 2):
                window.grab().save(str(destination / f"{name}_{width}x{height}.png"))
    window.hide()
    window.deleteLater()


if __name__ == "__main__":
    if "--screenshots" in sys.argv:
        screenshots()
        sys.argv.remove("--screenshots")
    unittest.main()
