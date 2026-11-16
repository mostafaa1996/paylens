from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QLabel,
    QDoubleSpinBox, QSplitter, QMessageBox, QProgressBar)
from .stack_model import StackModel
from .domain import snapshot, new_id, now
from .widgets import RecordsModel, RecordTable, JsonView, button, row, note


class StackPage(QWidget):
    edit_requested = Signal(object)
    dispatch_requested = Signal(object)
    export_requested = Signal(object, str)
    stream_requested = Signal(float)

    def __init__(self, hooks):
        super().__init__()
        self.hooks, self.items = hooks, []
        self.cases = {}
        self.stack_id = new_id("stack")
        self.busy = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.merchant = QComboBox()
        for merchant_id, name in (
            (21, "Nile Electronics"), (22, "Alex Fashion"), (23, "Delta Market"),
            (24, "Cairo Home"), (25, "Red Sea Sports"),
        ):
            self.merchant.addItem(f"{name} ({merchant_id})", merchant_id)
        self.merchant.setToolTip("Merchant for the next stack send or normal stream. Running sends keep their selection.")
        self.terminal = QComboBox()
        self.terminal.addItem('Online', 'online')
        self.terminal.setToolTip('Connection mode for the next selected case or new stream. Existing stack cases keep their selection.')
        layout.addWidget(row(QLabel("Merchant"), self.merchant, self.terminal,
                             button("Edit selected", self.edit), button("Remove", self.remove),
                             button("Clear stack", self.clear), button("Export all as JSON…", self.export_all)))
        self.model = StackModel(self.items)
        self.model.edited.connect(self.inspect)
        self.model.error.connect(self.hooks.feedback.emit)
        self.table = RecordTable(self.model)
        self.preview = JsonView()
        self.table.selectionModel().selectionChanged.connect(self.inspect)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.table)
        split.addWidget(self.preview)
        split.setSizes([330, 220])
        layout.addWidget(split, 1)
        self.send_button = button("→ Send Stack", self.send, True)
        self.stream_interval = QDoubleSpinBox()
        self.stream_interval.setRange(0.1, 3600)
        self.stream_interval.setValue(5)
        self.stream_interval.setSuffix(" s between case starts")
        self.stream_interval.setDecimals(1)
        self.stream_button = button("Start normal stream", lambda: self.stream_requested.emit(self.stream_interval.value()))
        self.stream_status = note("Stream stopped")
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("Idle")
        self.stream_interval.setMaximumWidth(230)
        controls = row(self.send_button, self.progress, self.stream_interval,
                       self.stream_button, self.stream_status)
        controls.layout().setStretch(1, 1)
        layout.addWidget(controls)
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.table)
        self.delete_shortcut.setContext(Qt.WidgetShortcut)
        self.delete_shortcut.activated.connect(self.remove)
        self.refresh()

    def refresh(self):
        active = {item['case_run'] for item in self.items}
        self.cases = {key: case for key, case in self.cases.items() if key in active}
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

    def add(self, item):
        self.items.append(snapshot(item))
        self.refresh()

    def update_payload(self, token, payload):
        item = next((item for item in self.items if item['token'] == token), None)
        if item is not None:
            item['payload'] = snapshot(payload)
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

    def send(self):
        if self.busy:
            return
        if self.items:
            self.dispatch_requested.emit(snapshot(self.items))
        else:
            self.hooks.feedback.emit("There are no stack events to send.")

    def update_item(self, result):
        self.update_payload(result['token'], result['payload'])

    def set_running(self, busy):
        self.busy = busy
        self.model.busy = busy
        self.send_button.setEnabled(not busy)

    def set_streaming(self, running, stopping=False):
        self.stream_button.setText("Stopping stream…" if stopping else "Stop normal stream" if running else "Start normal stream")
        self.stream_button.setEnabled(not stopping)
        self.stream_interval.setEnabled(not running)
        self.stream_status.setText("Finishing active cases…" if stopping else "Normal case streaming" if running else "Stream stopped")


class HistoryPage(QWidget):
    """Read-only session log of stack and streaming send outcomes."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = RecordsModel([
            ("Time", "dispatched_at"),
            ("Source", lambda record: "Streaming" if record.get("stream") else "Stack"),
            ("Case ID", "case_id"),
            ("Event type", lambda record: record["payload"].get("event_type") or record.get('action')),
            ("Event ID", lambda record: record["payload"].get("event_id")),
            ("Result", lambda record: {"accepted": "Sent", "failed": "Failed", "checkpoint": "Observation checkpoint"}.get(record["outcome"], record["outcome"])),
            ("Error", "transport_error"),
        ])
        self.records = self.model.records
        self.table = RecordTable(self.model)
        self.preview = JsonView()
        self.preview.set_payload({})
        self.table.selectionModel().selectionChanged.connect(self.inspect)
        split = QSplitter(Qt.Vertical)
        split.addWidget(self.table)
        split.addWidget(self.preview)
        split.setSizes([380, 220])
        layout.addWidget(split)

    def record(self, item):
        record = snapshot(item)
        record.setdefault("dispatched_at", now())
        record.setdefault("outcome", "unknown")
        record.setdefault("transport_error", "")
        index = len(self.records)
        self.model.beginInsertRows(QModelIndex(), index, index)
        self.records.append(record)
        self.model.endInsertRows()
        self.table.scrollToBottom()

    def inspect(self, *_):
        selected = self.table.selected_rows()
        self.preview.set_payload(self.records[selected[0]]["payload"] if selected else {})
