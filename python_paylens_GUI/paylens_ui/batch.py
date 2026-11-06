"""CSV configuration and editable bounded fixtures; deliberately no CSV engine."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QTabWidget,
    QCheckBox, QComboBox, QLineEdit, QSpinBox, QLabel, QDialog, QDialogButtonBox, QMessageBox)
from .domain import CSV_SCHEMAS, csv_rows, snapshot
from .widgets import RecordsModel, RecordTable, JsonView, button, row, note, scroll


EXCEPTIONS = {
    "Missing linked record": "Omit a capture/settlement/allocation match; no financial inference is performed.",
    "Unmatched record": "Use an identifier absent from the other normal preview files.",
    "Amount mismatch": "Change a monetary column to differ from the linked fixture.",
    "Wrong currency": "Use a different currency on one row.",
    "Wrong merchant / provider scope": "Use an inconsistent merchant or provider-account ID.",
    "Missing stable identifier": "Replace a stable identifier with null.",
    "Duplicate stable identifier / row": "Repeat one exact sample row.",
    "Repeated report": "Repeat a report snapshot without creating a new financial identity.",
    "Corrected report version": "Preview report_version 2 where the dataset supports it.",
    "Older snapshot arriving later": "Set an older snapshot time; arrival configuration is separate.",
    "Missing / incorrect allocation": "Remove an allocation row or change its settlement entry reference.",
    "Allocation amount mismatch": "Change the provider-supplied allocation amount.",
    "Absent provider allocation report": "No allocation preview; no derived allocation is invented.",
    "Payout SCHEDULED": "A scheduled status snapshot, not a bank credit.",
    "Payout FAILED": "A failed payout status snapshot.",
    "Payout RETURNED": "A returned payout status snapshot.",
    "Missing / delayed bank credit": "Omit a bank credit preview; no inference from payout status.",
    "Unmatched bank credit": "Change bank transfer reference to an unmatched synthetic value.",
    "Mismatched transfer reference / account": "Change transfer/account identifiers.",
    "Empty file": "Show zero sample rows.",
    "Missing column": "Omit the first contract column in this intentionally invalid preview.",
    "Invalid date / decimal": "Set a date or decimal cell to deliberately malformed text.",
    "Null in required column": "Set a required column to explicit null.",
}


class DatasetTab(QWidget):
    def __init__(self, name, columns, rows):
        super().__init__()
        self.name, self.columns, self.normal = name, columns, snapshot(rows)
        self.available = True
        layout = QVBoxLayout(self)
        self.enabled = QCheckBox("Include this dataset")
        self.enabled.setChecked(True)
        self.filename = QLabel(name)
        layout.addWidget(row(self.enabled, self.filename))
        self.state = note("")
        self.state.hide()
        layout.addWidget(self.state)
        self.model = RecordsModel([(key, key, hint) for key, hint in columns], snapshot(rows), editable=True)
        self.table = RecordTable(self.model)
        layout.addWidget(self.table, 1)
        self.row_count = note("")
        layout.addWidget(row(self.row_count, button("Add sample row", self.add_row), button("Delete selected rows", self.delete_rows)))
        self.table.model().dataChanged.connect(self.update_count)
        self.table.verticalHeader().setToolTip("* marks a manually modified row. Enter <null> for null; empty cells stay empty strings.")
        exceptions = QGroupBox("Exception configuration • intentional invalid preview")
        el = QVBoxLayout(exceptions)
        self.exception_enabled = QCheckBox("Enable exceptions for this file")
        self.preset = QComboBox()
        self.preset.addItems(EXCEPTIONS)
        self.measure = QComboBox()
        self.measure.addItems(["Count", "Percentage"])
        self.exception_count = QSpinBox()
        self.exception_count.setRange(0, 100000000)
        self.exception_count.setValue(1)
        self.measure.currentTextChanged.connect(lambda text: self.exception_count.setMaximum(100 if text == "Percentage" else 100000000))
        self.seed = QLineEdit("42")
        self.seed.setPlaceholderText("Optional seed")
        self.targets = QLineEdit("")
        self.targets.setPlaceholderText("Optional target IDs, comma separated")
        el.addWidget(row(self.exception_enabled, self.preset))
        el.addWidget(row(self.measure, self.exception_count, QLabel("Seed"), self.seed, self.targets))
        self.description = note(EXCEPTIONS[self.preset.currentText()])
        self.preset.currentTextChanged.connect(lambda t: self.description.setText(EXCEPTIONS[t]))
        el.addWidget(self.description)
        el.addWidget(button("Apply one bounded exception example", self.apply_exception))
        layout.addWidget(exceptions)
        notes = "\n".join(f"{i+1}. {key} — {hint}" for i, (key, hint) in enumerate(columns))
        self.column_notes = note(notes)
        self.column_notes.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info = QGroupBox("Ordered columns and known contract notes")
        il = QVBoxLayout(info)
        il.addWidget(self.column_notes)
        layout.addWidget(info)
        self.update_count()

    def update_count(self, *_):
        self.row_count.setText(f"{len(self.model.records)} sample rows • {len(self.model.modified)} modified • <null> = null")

    def set_state(self, message):
        self.state.setText(message)
        self.state.setVisible(bool(message))

    def add_row(self):
        if len(self.model.records) >= 100:
            self.set_state("Preview is bounded to 100 sample rows; generation scale is configured in Settings.")
            return
        self.model.records.append({key: "" for key, _ in self.columns})
        self.model.modified.add(len(self.model.records) - 1)
        self.model.refresh()
        self.update_count()

    def delete_rows(self):
        for i in reversed(self.table.selected_rows()):
            del self.model.records[i]
        self.model.modified = set(range(len(self.model.records)))
        self.model.refresh()
        self.update_count()

    def restore(self):
        self.model.columns = [(key, key, hint) for key, hint in self.columns]
        self.model.modified.clear()
        self.model.refresh(snapshot(self.normal) if self.available else [])
        self.set_state("SIMULATED • normal deterministic fixture • restored" if self.available else "Unavailable from simulated provider. No allocation derivation.")
        self.update_count()

    def apply_exception(self):
        if not self.available:
            self.set_state("Unavailable from simulated provider. Exception configuration retained; no report inferred.")
            return
        if not self.exception_enabled.isChecked():
            self.set_state("Enable exceptions to apply an intentionally invalid preview.")
            return
        self.restore()
        key = self.preset.currentText()
        rows = self.model.records
        first = rows[0] if rows else {}
        amount = next((k for k in first if "amount" in k), None)
        identity = next((k for k in first if k.endswith("_id")), None)
        if key in ("Empty file", "Missing linked record", "Missing / delayed bank credit", "Absent provider allocation report"):
            rows.clear()
        elif key in ("Duplicate stable identifier / row", "Repeated report"):
            rows.append(snapshot(first))
        elif key in ("Amount mismatch", "Allocation amount mismatch") and amount:
            first["allocated_net_amount" if "allocated_net_amount" in first else amount] = "981.00"
        elif key == "Wrong currency":
            first["currency" if "currency" in first else "transaction_currency"] = "USD"
        elif key == "Wrong merchant / provider scope":
            first["merchant_id"] = "mer_unmatched"
        elif key in ("Missing stable identifier", "Null in required column") and identity:
            first[identity] = None
        elif key == "Corrected report version":
            if "report_version" in first:
                first["report_version"] = "2"
            else:
                self.set_state("report_version is not a column in this dataset; preset configuration retained without inventing a column.")
                return
        elif key == "Older snapshot arriving later":
            date = next((k for k in first if k.endswith("_at") or k == "event_time"), None)
            if date:
                first[date] = "2001-01-01T00:00:00Z"
        elif key == "Missing / incorrect allocation":
            if "allocation_id" in first:
                first["entry_id"] = "entry_unmatched"
            else:
                rows.clear()
        elif key.startswith("Payout "):
            if "payout_amount" not in first:
                self.set_state("Payout status presets apply to the payouts dataset. Configuration retained.")
                return
            first["status"] = key.split()[-1]
            first["sent_at"] = None
        elif key in ("Mismatched transfer reference / account", "Unmatched bank credit"):
            ref = "transfer_reference" if "transfer_reference" in first else "bank_transfer_reference" if "bank_transfer_reference" in first else identity
            first[ref] = "unmatched_demo"
        elif key == "Missing column":
            self.model.columns = self.model.columns[1:]
            for item in rows:
                item.pop(self.columns[0][0], None)
        elif key == "Invalid date / decimal":
            first[amount or next((k for k in first if "date" in k), identity)] = "INVALID_TEST_VALUE"
        else:
            first[identity] = "unmatched_demo"
        self.model.modified = set(range(len(rows)))
        self.model.refresh()
        self.set_state(f"SIMULATED • INTENTIONALLY INVALID preview • {key} • one bounded example, configured scale is deferred")
        self.update_count()

    def config(self, null_text="", header=True):
        return dict(dataset=self.name, enabled=self.enabled.isChecked(), filename=self.filename.text(), null=null_text, header=header,
                    sample_rows=snapshot(self.model.records), exceptions=dict(enabled=self.exception_enabled.isChecked(), preset=self.preset.currentText(),
                    measure=self.measure.currentText(), value=self.exception_count.value(), seed=self.seed.text(), target_ids=self.targets.text(), description=self.description.text()))


class BatchPage(QWidget):
    def __init__(self, hooks):
        super().__init__()
        self.hooks = hooks
        self.approximate_scale, self.generation_seed = "1000", "42"
        self.output_directory = "output"
        self.delimiter_value, self.encoding_value = ",", "UTF-8"
        self.null_value, self.include_headers = "", True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.datasets = []
        rows = csv_rows()
        for (name, columns), title in zip(CSV_SCHEMAS.items(), ["Settlement", "Payouts", "Allocations", "Bank statement", "Capture Ledger • INTERNAL"]):
            tab = DatasetTab(name, columns, rows[name])
            self.datasets.append(tab)
            self.tabs.addTab(scroll(tab), title)
        layout.addWidget(self.tabs, 1)
        self.summary = note("")
        layout.addWidget(self.summary)
        layout.addWidget(row(button("Generate selected files…", self.generate, True),
                             button("Export all five…", self.export_all)))
        for tab in self.datasets:
            tab.filename.setText(tab.name.replace("ACCOUNT", "<account>").replace("DATE", "<date>"))
        for tab in self.datasets:
            tab.enabled.toggled.connect(self.update_summary)
        self.update_summary()

    def apply_settings(self, values):
        self.approximate_scale = values["approximate_scale"]
        self.generation_seed = values["seed"]
        self.output_directory = values["output_dir"]
        self.delimiter_value = values["delimiter"]
        self.encoding_value = values["encoding"]
        self.null_value = values["null"]
        self.include_headers = values["headers"]
        self.update_summary()

    def update_summary(self, *_):
        self.summary.setText(f"{sum(t.enabled.isChecked() for t in self.datasets)} / 5 datasets selected • previews contain a few rows only • output: {self.output_directory}")

    def config(self, all_files=False):
        return dict(approximate_scale=self.approximate_scale, seed=self.generation_seed, output_directory=self.output_directory,
                    delimiter=self.delimiter_value, encoding=self.encoding_value,
                    files=[t.config(self.null_value, self.include_headers) for t in self.datasets if all_files or t.enabled.isChecked()])

    def confirm(self, title, config):
        if not config["files"]:
            self.hooks.feedback.emit("Select at least one dataset.")
            return False
        if not config["approximate_scale"].isdigit():
            self.hooks.feedback.emit("Approximate scale must be a nonnegative integer.")
            return False
        dialog = QDialog(self)
        dialog.setWindowTitle(title + " • SIMULATED")
        dialog.resize(750, 650)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note("Review intended files, generation scale, exceptions, and sample rows. Only a mock hook runs; no files are generated or saved."))
        view = JsonView()
        view.set_payload(config)
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return dialog.exec() == QDialog.Accepted

    def generate(self):
        config = self.config()
        if self.confirm("Generate selected files", config):
            self.hooks.request_generate_batch_files.emit(config)
            for tab in self.datasets:
                if tab.enabled.isChecked():
                    tab.set_state("SIMULATED: configuration received; bounded sample only. No file generated.")

    def export_all(self):
        config = self.config(all_files=True)
        if self.confirm("Export all five", config):
            self.hooks.export_dialog("CSV configurations and previews", config["files"], config)
