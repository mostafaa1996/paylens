import json
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QComboBox, QMessageBox, QDialog
from .domain import entities, snapshot, new_id
from .widgets import RecordsModel, RecordTable, ConfigDialog, button, row, note


class EntityPage(QWidget):
    changed = Signal()

    def __init__(self, kind, hooks, reference_check):
        super().__init__()
        self.kind, self.hooks, self.reference_check = kind, hooks, reference_check
        self.records = entities(kind)
        self.id_key = "customer_id" if kind == "customers" else "merchant_id"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(note("PROPOSED UI MODEL • synthetic fixtures only. These entity fields are not supplied PayLens event contracts. Account references are synthetic IDs."))
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"Search {kind} by ID, name, status, or defaults…")
        self.filter = QComboBox()
        self.filter.addItems(["All statuses", "active", "inactive"])
        layout.addWidget(row(self.search, self.filter))
        layout.addWidget(row(button("+ Add manually", self.add, True), button("Edit", self.edit),
                             button("Disable", self.disable), button("Remove from demo", self.remove)))
        columns = [(key.replace("_", " ").title(), key) for key in self.records[0]]
        self.model = RecordsModel(columns)
        self.table = RecordTable(self.model)
        layout.addWidget(self.table, 1)
        self.counts = note("")
        layout.addWidget(self.counts)
        layout.addWidget(row(button("Automatic generation…", self.generate),
                             button("Export…", lambda: hooks.export_dialog(kind, snapshot(self.records)))))
        self.search.textChanged.connect(self.refresh)
        self.filter.currentTextChanged.connect(self.refresh)
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self.table)
        self.delete_shortcut.setContext(Qt.WidgetShortcut)
        self.delete_shortcut.activated.connect(self.remove)
        self.refresh()

    def selected(self):
        indices = self.table.selected_rows()
        return self.model.records[indices[0]] if indices else None

    def refresh(self, *_):
        self.model.refresh([r for r in self.records if self.search.text().casefold() in json.dumps(r).casefold() and (not self.filter.currentIndex() or r.get("status") == self.filter.currentText())])
        self.counts.setText(f"{len(self.model.records)} visible / {len(self.records)} in-memory records. Manual event overrides stay unchanged when entity defaults change.")

    def record_dialog(self, initial):
        dialog = ConfigDialog(f"{self.kind.title()} • proposed UI record", initial, self)
        # Entity models intentionally have no official schema; this is local presentation policy.
        while dialog.exec() == QDialog.Accepted:
            value = dialog.value
            value["ui_test_record"] = True
            return value
        return None

    def add(self):
        initial = snapshot(entities(self.kind)[0])
        initial[self.id_key] = new_id("cus" if self.kind == "customers" else "mer")
        initial["display_name"] = "Synthetic demo record"
        value = self.record_dialog(initial)
        if value is not None:
            self.records.append(value)
            self.refresh()
            self.changed.emit()

    def edit(self):
        selected = self.selected()
        if selected:
            value = self.record_dialog(snapshot(selected))
            if value is not None:
                selected.clear()
                selected.update(value)
                self.refresh()
                self.changed.emit()

    def disable(self):
        if self.selected():
            self.selected()["status"] = "inactive"
            self.refresh()
            self.changed.emit()

    def remove(self):
        selected = self.selected()
        if selected:
            refs = self.reference_check(self.id_key, selected.get(self.id_key))
            if refs and QMessageBox.question(self, "Referenced record", f"This ID appears in {refs} draft/stack snapshot(s). Remove the fixture? Existing payloads will retain the ID.") != QMessageBox.Yes:
                return
            self.records = [r for r in self.records if r is not selected]
            self.refresh()
            self.changed.emit()

    def generate(self):
        defaults = dict(count=100, seed="42", id_prefix="cus" if self.kind == "customers" else "mer", active_percent=90,
                        country="EG", default_currency="EGP", provider_id="provider_demo", provider_account_id="pa_demo")
        dialog = ConfigDialog("Automatic generation • bounded demo", defaults, self)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.value
            if type(config.get("count")) is not int or config["count"] < 1:
                self.hooks.feedback.emit("Count must be a positive integer.")
                return
            getattr(self.hooks, f"request_generate_{self.kind}").emit(config)
            # Fixed fixtures only, regardless of the future requested scale.
            for i, record in enumerate(entities(self.kind)[:3]):
                record[self.id_key] = f"{config.get('id_prefix')}_demo_{len(self.records) + i + 1}"
                record["status"] = "active" if i < 2 else "inactive"
                record["ui_scenario"] = "SIMULATED generation preview"
                for key in ("country", "default_currency", "provider_id", "provider_account_id"):
                    if key in record and config.get(key):
                        record[key] = config[key]
                self.records.append(record)
            self.refresh()
            self.changed.emit()
