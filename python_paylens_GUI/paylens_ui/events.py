from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QLineEdit, QLabel,
    QSpinBox, QSplitter, QMessageBox, QProgressBar, QDateEdit)
from .domain import snapshot, body, business_key, family, validate, new_id, now
from .widgets import RecordsModel, RecordTable, JsonView, button, row, note


def stack_columns():
    return [("Position", "position"), ("Event Type", lambda r: r["payload"].get("event_type")),
            ("Event ID", lambda r: r["payload"].get("event_id")),
            ("Merchant", lambda r: body(r["payload"]).get("merchant_id")),
            ("Payment / Order", lambda r: business_key(r["payload"])),
            ("Event Time", lambda r: r["payload"].get("event_time", r["payload"].get("emitted_at"))),
            ("Scenario", "scenario"), ("Validation", lambda r: "; ".join(validate(r["payload"], r["schema"])) or "No known issues"),
            ("UI Dispatch State", lambda r: r.get("state", "draft"))]


class StackPage(QWidget):
    edit_requested = Signal(object)
    dispatch_requested = Signal(object, object)
    export_requested = Signal(object, str)

    def __init__(self, hooks):
        super().__init__()
        self.hooks, self.items = hooks, []
        self.stack_id = new_id("stack")
        self.busy = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(row(button("Edit selected", self.edit), button("Remove", self.remove),
                             button("Clear stack", self.clear), button("Export all as JSON…", self.export_all)))
        self.model = RecordsModel(stack_columns(), self.items)
        self.table = RecordTable(self.model)
        self.preview = JsonView()
        self.table.selectionModel().selectionChanged.connect(self.inspect)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.table)
        split.addWidget(self.preview)
        split.setSizes([330, 220])
        layout.addWidget(split, 1)
        self.delay = QSpinBox()
        self.delay.setRange(0, 10000)
        self.delay.setValue(150)
        self.delay.setSuffix(" ms between events")
        self.delay.setMinimumWidth(230)
        self.send_button = button("→ Send Stack", self.send, True)
        self.retry_button = button("Retry failed", lambda: self.send(only_failed=True))
        self.resend_button = button("Resend selected (exact)", lambda: self.send(selected=True))
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
        layout.addWidget(row(self.delay, self.send_button, self.retry_button, self.resend_button, self.progress))
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.table)
        self.delete_shortcut.setContext(Qt.WidgetShortcut)
        self.delete_shortcut.activated.connect(self.remove)
        self.refresh()

    def refresh(self):
        for i, item in enumerate(self.items):
            item["position"] = i + 1
        self.model.refresh(self.items)

    def selected(self):
        return [self.items[i] for i in self.table.selected_rows()]

    def inspect(self, *_):
        selected = self.selected()
        self.preview.set_payload(selected[0]["payload"] if selected else {})

    def export_all(self):
        if not self.items:
            self.hooks.feedback.emit("There are no stack events to export.")
            return
        self.export_requested.emit([snapshot(item["payload"]) for item in self.items], self.stack_id)

    def add(self, payload, metadata):
        token = metadata.get("edit_token")
        if token:
            item = next((r for r in self.items if r["token"] == token), None)
            if item:
                item.update(payload=snapshot(payload), scenario=metadata["scenario"], testing=metadata["testing"], state="draft")
        else:
            self.items.append(dict(payload=snapshot(payload), **{k: v for k, v in metadata.items() if k != "edit_token"}, token=new_id("item"), state="draft", stack_id=self.stack_id))
        self.refresh()

    def edit(self):
        if not self.busy and self.selected():
            self.edit_requested.emit(snapshot(self.selected()[0]))

    def remove(self):
        if self.busy:
            return
        for index in reversed(self.table.selected_rows()):
            del self.items[index]
        self.refresh()

    def clear(self):
        if not self.busy and self.items and QMessageBox.question(self, "Clear stack?", "Remove all in-memory stack drafts?") == QMessageBox.Yes:
            self.items.clear()
            self.refresh()

    def options(self):
        return dict(delay_ms=self.delay.value())

    def send(self, checked=False, only_failed=False, selected=False):
        if self.busy:
            return
        items = self.selected() if selected else [r for r in self.items if not only_failed or r.get("outcome") == "failed"]
        if items:
            self.dispatch_requested.emit(snapshot(items), self.options())
        else:
            self.hooks.feedback.emit("No matching stack entries selected.")

    def update_item(self, item):
        for existing in self.items:
            if existing["token"] == item["token"]:
                for key in ("state", "outcome", "run_id", "attempt_id", "dispatched_at", "transport_error", "kafka_partition", "kafka_offset", "topic_name"):
                    if key in item:
                        existing[key] = item[key]
        self.refresh()

    def set_running(self, busy):
        self.busy = busy
        for w in (self.send_button, self.retry_button, self.resend_button):
            w.setEnabled(not busy)


class HistoryPage(QWidget):
    load_requested = Signal(object)

    def __init__(self, hooks, settings):
        super().__init__()
        self.hooks, self.settings, self.records = hooks, settings, []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search event / merchant / payment / attempt / capture / refund / order / scenario / stack / run…")
        self.family_filter = QComboBox()
        self.family_filter.addItems(["All families", "Authorization", "Capture", "Refund", "Fulfillment"])
        self.outcome = QComboBox()
        self.outcome.addItems(["All outcomes", "prepared", "accepted", "failed"])
        layout.addWidget(row(self.search, self.family_filter, self.outcome))
        self.from_date, self.to_date = QDateEdit(QDate(2000, 1, 1)), QDateEdit(QDate(2099, 12, 31))
        self.from_date.setCalendarPopup(True)
        self.to_date.setCalendarPopup(True)
        self.demo_state = QComboBox()
        self.demo_state.addItems(["Live in-memory history", "Empty state", "Loading state", "Error state"])
        layout.addWidget(row(QLabel("Dispatch date from"), self.from_date, QLabel("to"), self.to_date, self.demo_state))
        self.message = note("No history yet. Prepare or dispatch an event, or load demo history.")
        layout.addWidget(self.message)
        self.model = RecordsModel([("Family", lambda r: family(r["payload"])), ("Business group", lambda r: business_key(r["payload"])),
                                   ("Event ID", lambda r: r["payload"].get("event_id")), ("Outcome", lambda r: {"accepted": "Kafka ACK", "failed": "Kafka failed", "cancelled": "Cancelled"}.get(r["outcome"], r["outcome"])), ("Dispatch time", "dispatched_at"),
                                   ("Scenario", "scenario"), ("Run", "run_id"), ("File save", "save_state")])
        self.table = RecordTable(self.model)
        self.table.selectionModel().selectionChanged.connect(self.inspect)
        self.preview = JsonView()
        self.timeline = JsonView()
        detail = QSplitter()
        detail.addWidget(self.preview)
        detail.addWidget(self.timeline)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.table)
        split.addWidget(detail)
        split.setSizes([300, 270])
        layout.addWidget(split, 1)
        layout.addWidget(row(button("Load demo history", self.demo), button("Load as new draft", self.load),
                             button("Copy JSON", self.preview.copy), button("Export…", self.export),
                             button("Request / retry save", self.retry_save), button("Demo save failure", self.save_failure)))
        self.path_label = note("Filename previews only. Each raw event has a separate file; dispatch attempts belong in a future sidecar/index.")
        layout.addWidget(self.path_label)
        for signal in (self.search.textChanged, self.family_filter.currentTextChanged, self.outcome.currentTextChanged,
                       self.from_date.dateChanged, self.to_date.dateChanged, self.demo_state.currentTextChanged):
            signal.connect(self.refresh)

    def record(self, item):
        rec = snapshot(item)
        rec.setdefault("dispatched_at", now())
        rec.setdefault("outcome", "prepared")
        rec.setdefault("run_id", new_id("prepared"))
        rec.setdefault("attempt_id", new_id("snapshot"))
        autosave = self.settings().get("autosave") and rec["outcome"] in ("accepted", "failed")
        rec["save_state"] = "pending integration" if autosave else "not requested"
        self.records.append(rec)
        if autosave:
            self.hooks.request_save_history.emit(snapshot(rec["payload"]), self.metadata(rec))
        self.refresh()

    def metadata(self, rec):
        return {k: snapshot(v) for k, v in rec.items() if k != "payload"}

    def refresh(self, *_):
        query = self.search.text().casefold()
        rows = []
        if self.demo_state.currentIndex() == 0:
            for rec in self.records:
                text = str(rec).casefold()
                date = QDate.fromString(rec["dispatched_at"][:10], "yyyy-MM-dd")
                if query in text and (not self.family_filter.currentIndex() or family(rec["payload"]) == self.family_filter.currentText()) and (not self.outcome.currentIndex() or rec["outcome"] == self.outcome.currentText()) and self.from_date.date() <= date <= self.to_date.date():
                    rows.append(rec)
        self.model.refresh(rows)
        self.message.setText([f"{len(rows)} snapshots / attempts • in memory • Kafka broker delivery results" if rows else "No matching history. Dispatch an event or load demo history.",
                              "History is empty. Dispatch an event to begin.", "Loading history… (demo state)",
                              "History unavailable (demo error). Select Live in-memory history to retry."][self.demo_state.currentIndex()])

    def selected(self):
        indices = self.table.selected_rows()
        return self.model.records[indices[0]] if indices else None

    def inspect(self, *_):
        rec = self.selected()
        if not rec:
            self.preview.set_payload({})
            self.timeline.set_payload([])
            return
        self.preview.set_payload(rec["payload"])
        related = sorted([r for r in self.records if business_key(r["payload"]) == business_key(rec["payload"])], key=lambda r: str(r["payload"].get("event_time", r["payload"].get("emitted_at", ""))))
        self.timeline.set_payload({"business_group": business_key(rec["payload"]), "chronological_timeline": [dict(event_id=r["payload"].get("event_id"), event_time=r["payload"].get("event_time", r["payload"].get("emitted_at")), outcome=r["outcome"], attempt_id=r["attempt_id"], run_id=r["run_id"]) for r in related], "selected_metadata": self.metadata(rec)})
        # Unique attempt suffix prevents duplicate/replay overwrite in a future service.
        import re
        event = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(rec["payload"].get("event_id", "unknown")))[:100]
        self.path_label.setText(f"Preview only: {self.settings()['history_dir']}/{rec['run_id']}/{family(rec['payload']).lower()}/{event}__{rec['attempt_id']}.json")

    def load(self):
        if self.selected():
            rec = snapshot(self.selected())
            rec["payload"]["event_id"] = new_id()
            self.load_requested.emit(rec)

    def export(self):
        if self.selected():
            self.hooks.export_dialog("history raw JSON", [self.selected()["payload"]])

    def retry_save(self):
        if self.selected():
            rec = self.selected()
            rec["save_state"] = "pending integration"
            self.hooks.request_save_history.emit(snapshot(rec["payload"]), self.metadata(rec))
            self.refresh()

    def save_failure(self):
        if self.selected():
            self.selected()["save_state"] = "SIMULATED save failed"
            self.refresh()

    def demo(self):
        from .domain import SAMPLES
        for name, payload in SAMPLES.items():
            self.record(dict(payload=payload, schema=name, scenario="Exact supplied sample • independent fixture", outcome="prepared", testing=False))
        self.demo_state.setCurrentIndex(0)
