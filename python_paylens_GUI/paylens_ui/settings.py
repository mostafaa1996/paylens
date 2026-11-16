from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QGroupBox, QComboBox, QLineEdit, QCheckBox
from .widgets import DirectoryInput, button, row, note, scroll


class SettingsPage(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        content = QWidget()
        cl = QVBoxLayout(content)
        integration = QGroupBox("Event Hubs publishing")
        form = QFormLayout(integration)
        form.addRow("Connection settings", note("EVENTHUB_CONNECTION_STRING is loaded from python_paylens_GUI/.env. Messages use the existing Event Hubs sender and its auth_req hub. Connection is checked when sending."))
        cl.addWidget(integration)
        persistence = QGroupBox("Export preferences • in memory only")
        pf = QFormLayout(persistence)
        self.json_indent = QComboBox()
        self.json_indent.addItems(["2 spaces", "4 spaces"])
        pf.addRow("JSON export indentation", self.json_indent)
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

    def values(self):
        return dict(output_dir=self.output_dir.edit.text(),
                    approximate_scale=self.approximate_scale.text(), seed=self.generation_seed.text(),
                    json_indent=2 if not self.json_indent.currentIndex() else 4, delimiter=self.csv_delimiter.currentText(), encoding=self.encoding.currentText(),
                    null=self.csv_null.text(), headers=self.headers.isChecked())

