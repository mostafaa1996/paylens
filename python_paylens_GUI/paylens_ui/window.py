import json
from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QButtonGroup, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QCheckBox, QFileDialog)
from pathlib import Path
from .domain import SAMPLES, snapshot, validate, new_id
from .services import IntegrationHooks, KafkaDispatchWorker
from .widgets import button, row, note, DirectoryInput
from .theme import THEME, ensure_fonts
from .settings import SettingsPage
from .composer import Composer
from .events import StackPage, HistoryPage
from .entities import EntityPage
from .batch import BatchPage
from config import load_settings


class MainWindow(QMainWindow):
    PAGE_NAMES = ["Event Composer", "Event Stack", "Batch Files", "Customers", "Merchants", "Event History", "Settings"]

    def __init__(self):
        super().__init__()
        ensure_fonts()
        self.setWindowTitle("PayLens Simulator")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(THEME)
        self.hooks = IntegrationHooks()
        self.hooks.export_dialog = self.export_dialog
        self.dispatch_running = False
        self.dispatch_thread = None
        self.dispatch_worker = None
        self._close_when_dispatch_finishes = False
        self.settings = SettingsPage(self.hooks)
        self.customers = EntityPage("customers", self.hooks, self.reference_count)
        self.merchants = EntityPage("merchants", self.hooks, self.reference_count)
        self.composer = Composer(self.hooks, self.selectors)
        self.stack = StackPage(self.hooks)
        self.history = HistoryPage(self.hooks, self.settings.values)
        self.batch = BatchPage(self.hooks)
        self.pages = QStackedWidget()
        for page in (self.composer, self.stack, self.batch, self.customers, self.merchants, self.history, self.settings):
            self.pages.addWidget(page)
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(205)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 12, 0, 18)
        brand = QLabel("PayLens")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        sl.addSpacing(30)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        for i, name in enumerate(self.PAGE_NAMES):
            nav = button(name, lambda checked=False, index=i: self.navigate(index))
            nav.setCheckable(True)
            self.nav.addButton(nav, i)
            sl.addWidget(nav)
        self.nav.button(0).setChecked(True)
        sl.addStretch()
        layout.addWidget(sidebar)
        workspace = QWidget()
        wl = QVBoxLayout(workspace)
        wl.setContentsMargins(22, 18, 22, 12)
        wl.setSpacing(12)
        self.title = QLabel("Transaction Event Generator")
        self.title.setObjectName("pageTitle")
        wl.addWidget(self.title)
        wl.addWidget(self.pages, 1)
        layout.addWidget(workspace, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Kafka dispatch - delivery status reported per event")
        self.hooks.feedback.connect(self.feedback)
        self.hooks.request_send_event.connect(self.start_single)
        self.hooks.request_send_stack.connect(self.start_dispatch)
        self.composer.add_requested.connect(self.add_to_stack)
        self.composer.send_requested.connect(self.hooks.request_send_event.emit)
        self.stack.dispatch_requested.connect(self.hooks.request_send_stack.emit)
        self.stack.edit_requested.connect(self.edit_stack)
        self.stack.export_requested.connect(self.export_stack_json)
        self.history.load_requested.connect(self.load_history)
        self.settings.changed.connect(self.apply_settings)
        self.customers.changed.connect(self.entities_changed)
        self.merchants.changed.connect(self.entities_changed)

    def feedback(self, message):
        self.statusBar().showMessage(message)

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        self.nav.button(index).setChecked(True)
        self.title.setText("Transaction Event Generator" if index == 0 else self.PAGE_NAMES[index])

    def selectors(self):
        return {"merchant_id": [str(r.get("merchant_id", "")) for r in self.merchants.records],
                "customer_id": [str(r.get("customer_id", "")) for r in self.customers.records]}

    def reference_count(self, key, value):
        def contains(obj):
            if isinstance(obj, dict):
                return obj.get(key, object()) == value or any(contains(v) for v in obj.values())
            if isinstance(obj, list):
                return any(contains(v) for v in obj)
            return False
        return sum(contains(p) for p in self.composer.drafts.values()) + sum(contains(r["payload"]) for r in self.stack.items)

    def entities_changed(self):
        # Update choices in place, retaining manual overrides and draft snapshots.
        for path, field in self.composer.form.fields.items():
            if path[-1] in self.selectors():
                combo = field.editor
                text = combo.currentText()
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(self.selectors()[path[-1]])
                combo.setCurrentText(text)
                combo.blockSignals(False)
        self.feedback("Demo entity records updated. Event drafts and captured snapshots retain their existing values.")

    def add_to_stack(self, payload, metadata):
        if self.dispatch_running:
            self.feedback("A Kafka dispatch is running. Wait or cancel pending items before changing the stack.")
            return
        self.stack.add(payload, metadata)
        self.history.record(dict(payload=payload, **{k: v for k, v in metadata.items() if k != "edit_token"}, outcome="prepared", stack_id=self.stack.stack_id))
        self.feedback("Draft snapshot captured in Event Stack and in-memory history.")

    def edit_stack(self, item):
        if self.composer.load_draft(item["payload"], item["schema"], item["token"], item):
            self.navigate(0)

    def load_history(self, item):
        if self.composer.load_draft(item["payload"], item["schema"], metadata=item):
            self.navigate(0)
            self.feedback("Loaded as a new draft with a new event ID. Original history snapshot remains unchanged.")

    def export_stack_json(self, payloads, stack_id):
        output_dir = Path(self.settings.values()["output_dir"]).expanduser()
        suggested_path = output_dir / f"event_stack_{stack_id}.json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export all stack events", str(suggested_path), "JSON files (*.json)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payloads, ensure_ascii=False, indent=self.settings.values()["json_indent"]) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", f"Could not write the JSON file:\n{exc}")
            return
        self.feedback(f"Exported {len(payloads)} event(s) to {target}")

    def start_single(self, payload, metadata):
        item = dict(payload=snapshot(payload), 
                    **{k: v for k, v in metadata.items() if k != "edit_token"}, 
                    token=new_id("single"), 
                    state="draft")
        self.start_dispatch([item], dict(delay_ms=0))

    def start_dispatch(self, items, options):
        if self.dispatch_running:
            self.feedback("A Kafka dispatch is already running.")
            return
        if not items:
            self.feedback("There are no events to publish.")
            return

        invalid = []
        for index, item in enumerate(items, start=1):
            payload = item.get("payload")
            if not isinstance(payload, dict):
                invalid.append(f"item {index}: payload must be a JSON object")
                continue
            if not item.get("testing"):
                invalid.extend(f"item {index}: {issue}" for issue in validate(payload, item.get("schema")))
        if invalid:
            QMessageBox.warning(self, "Kafka publish blocked", "Correct these known sample-shape issues before publishing:\n" + "\n".join(invalid))
            return

        try:
            settings = load_settings()
        except (OSError, ValueError) as exc:
            self.feedback(f"Kafka configuration error: {exc}")
            return

        topic_by_event_type = {
            "authorization_requested": settings.topic_auth_requests,
            "authorization_result": settings.topic_auth_responses,
            "capture_expected": settings.topic_capture_expectations,
            "capture_result": settings.topic_capture_results,
            "refund.updated": settings.topic_refund,
            "order_fulfillment_updated": settings.topic_order_fulfillment,
        }
        planned = []
        for item in items:
            event_type = item["payload"].get("event_type")
            topic_name = topic_by_event_type.get(event_type)
            if not topic_name:
                self.feedback(f"Kafka publish blocked: no topic is configured for event_type {event_type!r}.")
                return
            planned_item = snapshot(item)
            for key in ("run_id", "attempt_id", "dispatched_at", "transport_error", "kafka_partition", "kafka_offset"):
                planned_item.pop(key, None)
            planned_item.update(topic_name=topic_name, state="Queued for Kafka", outcome="queued")
            planned.append(planned_item)

        self.dispatch_running = True
        self.stack.set_running(True)
        self.composer.send_button.setEnabled(False)
        self.composer.add_button.setEnabled(False)
        self.stack.progress.setRange(0, len(planned) * (2 if options.get("duplicate_dispatch") else 1))
        self.stack.progress.setValue(0)
        for item in planned:
            self.stack.update_item(item)

        thread = QThread(self)
        thread.setObjectName("KafkaDispatchThread")
        worker = KafkaDispatchWorker(planned, options, settings)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.item_updated.connect(self.item_updated)
        worker.progress.connect(self.progress)
        worker.finished.connect(self.completed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.dispatch_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self.dispatch_thread, self.dispatch_worker = thread, worker
        self.feedback(f"Publishing {len(planned)} event(s) to Kafka. Waiting for per-message broker acknowledgements.")
        thread.start()

    def cancel_dispatch(self):
        if self.dispatch_worker is not None and self.dispatch_running:
            self.dispatch_worker.cancel()
            self.feedback("Cancellation requested. The current Kafka publish will finish; unsent events will be cancelled.")

    def item_updated(self, item):
        self.stack.update_item(item)
        if item.get("outcome") in ("accepted", "failed"):
            self.history.record(item)
            if item.get("outcome") == "accepted":
                self.feedback(f"Kafka broker acknowledged {item['payload'].get('event_id')} at partition {item.get('kafka_partition')}, offset {item.get('kafka_offset')}. Consumer processing is separate.")
            else:
                self.feedback(f"Kafka publish failed for {item['payload'].get('event_id')}: {item.get('transport_error', 'delivery was not confirmed')}.")
        elif item.get("outcome") == "cancelled":
            self.feedback(f"Cancelled before Kafka publish: {item['payload'].get('event_id')}.")

    def progress(self, completed, total):
        self.stack.progress.setRange(0, max(total, 1))
        self.stack.progress.setValue(completed)
        self.stack.progress.setFormat(f"Kafka {completed}/{total}")

    def completed(self, results):
        accepted = sum(r["outcome"] == "accepted" for r in results)
        failed = sum(r["outcome"] == "failed" for r in results)
        cancelled = sum(r["outcome"] == "cancelled" for r in results)
        self.feedback(f"Kafka dispatch finished • {accepted} broker acknowledgements • {failed} failed • {cancelled} cancelled. A broker acknowledgement does not confirm consumer processing.")

    def dispatch_thread_finished(self):
        self.dispatch_running = False
        self.dispatch_worker = None
        self.dispatch_thread = None
        self.stack.set_running(False)
        self.composer.send_button.setEnabled(True)
        self.composer.add_button.setEnabled(True)
        if self._close_when_dispatch_finishes:
            self._close_when_dispatch_finishes = False
            self.close()

    def apply_settings(self):
        values = self.settings.values()
        self.batch.apply_settings(values)
        self.feedback("Session preferences applied. Kafka credentials and topics are read from .env when publishing.")

    def export_dialog(self, kind, selection, options=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Export request • SIMULATED")
        dialog.resize(620, 300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note(f"{kind} • {len(selection)} item(s). This invokes a future export hook. No files will be saved."))
        form = QFormLayout()
        directory = DirectoryInput(self.settings.values()["output_dir"])
        filename = QLineEdit("<event_id>__<attempt_id>.json" if "JSON" in kind or "event" in kind else "<dataset>_<date>.csv")
        form.addRow("Output directory", directory)
        form.addRow("Filename pattern preview", filename)
        raw = QCheckBox("Preserve original raw event payload; metadata belongs in sidecar/index")
        raw.setChecked(True)
        raw.setEnabled(False)
        form.addRow(raw)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            opts = snapshot(options or {})
            opts.update(output_directory=directory.edit.text(), filename_pattern=filename.text(), json_indent=self.settings.values()["json_indent"])
            self.hooks.request_export.emit(kind, snapshot(selection), opts)

    def closeEvent(self, event):
        if self.dispatch_running:
            if QMessageBox.question(self, "Kafka publish in progress", "Request cancellation of unsent events and close after the current publish completes?") != QMessageBox.Yes:
                event.ignore()
                return
            self._close_when_dispatch_finishes = True
            self.cancel_dispatch()
            event.ignore()
            return
        if self.stack.items or self.composer.dirty:
            if QMessageBox.question(self, "Close local workspace?", "Drafts, stack, history, and preferences are held in memory. Close and discard session state?") != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
