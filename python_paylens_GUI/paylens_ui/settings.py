from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QComboBox, QLineEdit, QSpinBox, QCheckBox
from .domain import SAMPLES
from .widgets import DirectoryInput, JsonView, button, row, note, scroll


class SettingsPage(QWidget):
    changed = Signal()

    def __init__(self, hooks):
        super().__init__()
        layout = QVBoxLayout(self)
        content = QWidget()
        cl = QVBoxLayout(content)
        integration = QGroupBox("Kafka publishing")
        form = QFormLayout(integration)
        form.addRow("Connection settings", note("Kafka broker credentials and topic names are loaded from python_paylens_GUI/.env. Broker connectivity is checked during publish."))
        self.url = QLineEdit("https://api.example.invalid")
        form.addRow("Future API base URL", self.url)
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 300)
        self.timeout.setValue(30)
        self.timeout.setSuffix(" seconds")
        form.addRow("Request timeout", self.timeout)
        form.addRow("Authentication", note("Future secure credential provider. Credentials are not collected or stored in this prototype."))
        self.routes = {}
        for sample in SAMPLES.values():
            kind = sample["event_type"]
            edit = QLineEdit("/events/" + kind.replace(".", "/"))
            self.routes[kind] = edit
            form.addRow(kind, edit)
        cl.addWidget(integration)
        persistence = QGroupBox("History and preferences • in memory only")
        pf = QFormLayout(persistence)
        self.history_dir = DirectoryInput("history")
        pf.addRow("History directory", self.history_dir)
        self.autosave = QCheckBox("Request one JSON file per event after dispatch")
        pf.addRow("Autosave", self.autosave)
        self.currency = QLineEdit("EGP")
        pf.addRow("Default currency", self.currency)
        self.timezone = QLineEdit("UTC")
        pf.addRow("Display / batch timezone", self.timezone)
        self.timestamps = QComboBox()
        self.timestamps.addItems(["Preserve supplied timestamps and offsets", "New helper timestamps in UTC"])
        pf.addRow("Timestamp policy", self.timestamps)
        self.json_indent = QComboBox()
        self.json_indent.addItems(["2 spaces", "4 spaces"])
        pf.addRow("Future JSON export indentation", self.json_indent)
        self.csv_null = QLineEdit("")
        pf.addRow("Default CSV null representation", self.csv_null)
        self.headers = QCheckBox("Include column headers")
        self.headers.setChecked(True)
        pf.addRow("CSV headers", self.headers)
        pf.addRow("Theme", note("PayLens Navy / Teal • light workspace"))
        pf.addRow(button("Apply session preferences", self.changed.emit, True))
        cl.addWidget(persistence)

        batch = QGroupBox("Batch file generation and output")
        bf = QFormLayout(batch)
        self.approximate_scale = QLineEdit("1000")
        self.generation_seed = QLineEdit("42")
        bf.addRow("Approximate scale / seed", row(self.approximate_scale, self.generation_seed))
        self.output_dir = DirectoryInput("output")
        bf.addRow("Output directory", self.output_dir)
        self.csv_delimiter = QComboBox()
        self.csv_delimiter.addItems([",", ";", "Tab", "|"])
        bf.addRow("CSV delimiter", self.csv_delimiter)
        self.encoding = QComboBox()
        self.encoding.addItems(["UTF-8", "UTF-8 with BOM"])
        bf.addRow("CSV encoding", self.encoding)
        cl.addWidget(batch)
        cl.addWidget(note("Preferences last for this session. Save/export actions request future integrations and never claim disk success. Existing event drafts retain their values."))
        cl.addStretch()
        layout.addWidget(scroll(content))
        self.hooks = hooks

    def values(self):
        return dict(base_url=self.url.text(), timeout=self.timeout.value(),
                    routes={k: v.text() for k, v in self.routes.items()}, history_dir=self.history_dir.edit.text(), output_dir=self.output_dir.edit.text(),
                    autosave=self.autosave.isChecked(), currency=self.currency.text(), timezone=self.timezone.text(),
                    approximate_scale=self.approximate_scale.text(), seed=self.generation_seed.text(),
                    json_indent=2 if not self.json_indent.currentIndex() else 4, delimiter=self.csv_delimiter.currentText(), encoding=self.encoding.currentText(),
                    null=self.csv_null.text(), headers=self.headers.isChecked())

