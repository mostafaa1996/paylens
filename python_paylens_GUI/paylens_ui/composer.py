import json
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel,
    QCheckBox, QLineEdit, QSplitter, QMessageBox)
from .domain import SAMPLES, snapshot, validate
from .widgets import PayloadForm, JsonView, button, row, note, scroll


class Composer(QWidget):
    add_requested = Signal(object, object)
    send_requested = Signal(object, object)

    def __init__(self, hooks):
        super().__init__()
        self.hooks = hooks
        self.drafts = {k: snapshot(v) for k, v in SAMPLES.items()}
        self.dirty = set()
        self.current_name = next(iter(SAMPLES))
        self.edit_token = None
        self.field_errors, self.raw_pending = [], False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.schema = QComboBox()
        self.schema.addItems(SAMPLES)
        self.scenario = QLineEdit("Manual draft")
        self.scenario.setPlaceholderText("Scenario label")
        layout.addWidget(row(QLabel("Schema family"), self.schema, self.scenario))
        layout.addWidget(row(button("Export JSON…", self.export)))
        self.splitter = QSplitter()
        self.left = QWidget()
        self.left_layout = QVBoxLayout(self.left)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.splitter.addWidget(self.left)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        self.raw = QCheckBox("Raw JSON mode")
        self.raw.toggled.connect(self.toggle_raw)
        self.apply_button = button("Apply raw JSON", self.apply_raw)
        self.apply_button.setEnabled(False)
        rl.addWidget(row(QLabel("LIVE PAYLOAD"), self.raw, self.apply_button, button("Copy JSON", lambda: self.preview.copy())))
        self.preview = JsonView()
        self.preview.textChanged.connect(self.raw_changed)
        rl.addWidget(self.preview, 1)
        self.summary = note("")
        summary_scroll = scroll(self.summary)
        summary_scroll.setMinimumHeight(55)
        summary_scroll.setMaximumHeight(95)
        rl.addWidget(summary_scroll)
        self.preset = QComboBox()
        self.preset.addItems(["Choose test preset…", "Null / omitted", "Mismatched IDs", "Abnormal amount", "Duplicate event ID", "Alternate status", "Old timestamp", "Malformed field"])
        rl.addWidget(row(self.preset, button("Apply preset", self.apply_preset)))
        self.splitter.addWidget(right)
        self.splitter.setSizes([600, 580])
        layout.addWidget(self.splitter, 1)
        self.add_button = button("+ Add to Stack", self.add, True)
        self.send_button = button("→ Send Single Event", self.send, True)
        self.edit_label = note("")
        layout.addWidget(row(self.edit_label, self.add_button, self.send_button))
        self.schema.currentTextChanged.connect(self.switch_schema)
        self.shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.shortcut.activated.connect(self.add)
        self.build_form()

    def build_form(self):
        while self.left_layout.count():
            widget = self.left_layout.takeAt(0).widget()
            widget.deleteLater()
        self.form = PayloadForm(self.drafts[self.current_name], SAMPLES[self.current_name])
        self.left_layout.addWidget(scroll(self.form))
        self.form.changed.connect(self.form_changed)
        _, self.field_errors = self.form.payload()
        self.refresh()

    def form_changed(self):
        payload, self.field_errors = self.form.payload()
        self.drafts[self.current_name] = payload
        self.dirty.add(self.current_name)
        self.refresh()

    def refresh(self, *_):
        payload = self.drafts[self.current_name]
        issues = self.field_errors + validate(payload, self.current_name)
        self.form.show_issues(issues)
        if not self.raw.isChecked():
            self.preview.blockSignals(True)
            self.preview.set_payload(payload)
            self.preview.blockSignals(False)
        status = "Testing mode • scenario payloads may include contract violations"
        self.summary.setText(status + ("\n" + "\n".join(issues) if issues else "\nNo known structural/type issues."))
        self.edit_label.setText(("Unsaved draft • " if self.current_name in self.dirty else "") + ("Editing stack snapshot" if self.edit_token else "In-memory only"))
        self.add_button.setText("✓ Update stack item" if self.edit_token else "+ Add to Stack")

    def switch_schema(self, name):
        if self.raw_pending:
            QMessageBox.information(self, "Apply raw edits", "Apply or discard raw edits before switching schema.")
            self.schema.blockSignals(True)
            self.schema.setCurrentText(self.current_name)
            self.schema.blockSignals(False)
            return
        self.current_name = name
        self.edit_token, self.field_errors = None, []
        self.build_form()

    def raw_changed(self):
        if self.raw.isChecked():
            self.raw_pending = True
            self.summary.setText("Raw edits are not applied. Apply JSON before adding or dispatching.")

    def toggle_raw(self, checked):
        if not checked and self.raw_pending:
            if QMessageBox.question(self, "Discard raw edits?", "Discard unapplied raw JSON changes?") != QMessageBox.Yes:
                self.raw.blockSignals(True)
                self.raw.setChecked(True)
                self.raw.blockSignals(False)
                return
            self.raw_pending = False
        self.preview.setReadOnly(not checked)
        self.left.setEnabled(not checked)
        self.apply_button.setEnabled(checked)
        self.refresh()

    def apply_raw(self):
        try:
            text = self.preview.toPlainText()
            if len(text) > 262144:
                raise ValueError("Raw editor limit is 256 KiB")
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise ValueError("An event must be an object. Malformed raw test transport is not supported.")
        except (ValueError, RecursionError) as exc:
            self.summary.setText(f"Cannot apply JSON: {exc}")
            return False
        self.drafts[self.current_name] = payload
        self.dirty.add(self.current_name)
        self.field_errors, self.raw_pending = [], False
        self.build_form()
        return True

    def ready(self):
        if self.raw_pending:
            QMessageBox.warning(self, "Unapplied JSON", "Apply raw JSON changes first.")
            return False
        issues = self.field_errors + validate(self.drafts[self.current_name], self.current_name)
        if self.field_errors:
            QMessageBox.warning(self, "Draft needs attention", "\n".join(issues))
            return False
        if not self.scenario.text().strip():
            QMessageBox.warning(self, "Scenario required", "Enter a scenario label for this testing payload.")
            return False
        return True

    def metadata(self):
        return dict(schema=self.current_name, 
                    scenario=self.scenario.text(), 
                    testing=True, 
                    edit_token=self.edit_token)

    def add(self):
        if self.ready():
            self.add_requested.emit(snapshot(self.drafts[self.current_name]), self.metadata())
            self.edit_token = None
            self.refresh()

    def send(self):
        if self.ready():
            self.send_requested.emit(snapshot(self.drafts[self.current_name]), self.metadata())

    def export(self):
        if self.ready():
            self.hooks.export_dialog("event JSON", [snapshot(self.drafts[self.current_name])])

    def load_draft(self, payload, schema, token=None, metadata=None):
        if self.raw_pending or schema in self.dirty:
            if QMessageBox.question(self, "Replace draft?", "Replace the current draft for this schema with the selected snapshot?") != QMessageBox.Yes:
                return False
        self.raw_pending = False
        self.raw.setChecked(False)
        self.current_name = schema
        self.schema.blockSignals(True)
        self.schema.setCurrentText(schema)
        self.schema.blockSignals(False)
        self.drafts[schema] = snapshot(payload)
        self.dirty.add(schema)
        self.field_errors = []
        self.edit_token = token
        if metadata:
            self.scenario.setText(metadata.get("scenario", "Stack edit"))
        self.build_form()
        return True

    def apply_preset(self):
        index = self.preset.currentIndex()
        if not index:
            return
        self.scenario.setText(self.preset.currentText())
        p = snapshot(self.drafts[self.current_name])
        b = p.get("data", p)
        if not isinstance(b, dict):
            return
        if index == 1:
            b["merchant_id"] = None
            b.pop("currency", None)
        elif index == 2:
            b["merchant_id"] = "mer_unmatched"
        elif index == 3:
            for key in b:
                if key.endswith("_minor"):
                    b[key] = -100000000000
        elif index == 4:
            p["event_id"] = "evt_duplicate_test"
        elif index == 5:
            b["status" if "status" in b else "fulfillment_status"] = "CUSTOM_TEST_STATUS"
        elif index == 6:
            p["emitted_at" if "emitted_at" in p else "event_time"] = "2001-01-01T00:00:00Z"
        elif index == 7:
            p["event_id"] = ["malformed", "identifier"]
        self.drafts[self.current_name] = p
        self.dirty.add(self.current_name)
        self.build_form()
