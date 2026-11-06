import json
import re
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStyle,
    QPlainTextEdit, QComboBox, QLineEdit, QFormLayout, QGroupBox, QScrollArea,
    QTableView, QAbstractItemView, QDialog, QDialogButtonBox, QFileDialog, QApplication)
from .domain import snapshot, expected_type, money, now, new_id


def button(text, callback, primary=False, parent=None):
    w = QPushButton(text, parent)
    w.setProperty("primary", primary)
    if primary:
        icon = QStyle.SP_ArrowRight if "Send" in text else QStyle.SP_FileIcon
        w.setIcon(w.style().standardIcon(icon))
    w.clicked.connect(callback)
    return w


def row(*widgets):
    w = QWidget()
    layout = QHBoxLayout(w)
    layout.setContentsMargins(0, 0, 0, 0)
    for item in widgets:
        layout.addWidget(item)
    return w


def note(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("muted", True)
    return label


def scroll(widget):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(widget)
    area.setFrameShape(QScrollArea.NoFrame)
    return area


class JsonHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text):
        for pattern, color in [(r'"(?:[^"\\]|\\.)*"\s*:', "#59d8cb"),
                               (r':\s*"(?:[^"\\]|\\.)*"', "#b9d997"),
                               (r'\b(?:true|false|null)\b', "#c9a4ef"),
                               (r'(?<![\w"])-?\d+(?:\.\d+)?', "#f4c777")]:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class JsonView(QPlainTextEdit):
    def __init__(self, readonly=True):
        super().__init__()
        self.setObjectName("jsonEditor")
        self.setFont(QFont("Consolas", 10))
        self.setReadOnly(readonly)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.highlighter = JsonHighlighter(self.document())
        self.setMinimumWidth(280)

    def set_payload(self, payload):
        self.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))

    def copy(self):
        QApplication.clipboard().setText(self.toPlainText())


MISSING = object()


class InlineMessage(QLabel):
    def __init__(self):
        super().__init__()
        self.hide()

    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))

    def clear(self):
        self.setText("")


class Field(QWidget):
    changed = Signal()

    def __init__(self, key, value, sample):
        super().__init__()
        self.key, self.sample = key, sample
        self.original = value if value is MISSING else snapshot(value)
        self.touched = False
        self.typ = expected_type(key, sample)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 3)
        layout.setSpacing(4)
        self.state = QComboBox()
        self.state.addItems(["Value", "Null", "Omitted"])
        self.state.setToolTip("Value, JSON null, and missing key are distinct. Strict checks use sample assumptions.")
        if value is MISSING:
            self.state.setCurrentText("Omitted")
        elif value is None:
            self.state.setCurrentText("Null")
        initial = sample if value is MISSING or value is None else value
        if self.typ in (dict, list):
            self.editor = JsonView(False)
            self.editor.setMinimumWidth(180)
            self.editor.setFixedHeight(100)
            self.editor.set_payload(initial if isinstance(initial, self.typ) else self.typ())
            self.editor.textChanged.connect(self.on_change)
        elif self.typ is bool:
            self.editor = QComboBox()
            self.editor.addItems(["true", "false"])
            self.editor.setCurrentText("true" if initial else "false")
            self.editor.currentTextChanged.connect(self.on_change)
        else:
            self.editor = QLineEdit("" if initial is None else str(initial))
            self.editor.setPlaceholderText("Integer minor units" if self.typ is int else "Empty string is a value")
            self.editor.textChanged.connect(self.on_change)
        top = row(self.editor, self.state)
        self.state.setMaximumWidth(95)
        layout.addWidget(top)
        if key.endswith("_minor"):
            self.equivalent = note("")
            layout.addWidget(self.equivalent)
        self.error = InlineMessage()
        self.error.setProperty("error", True)
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        if key == "event_id":
            layout.addWidget(button("New event ID", lambda: self.set_text_value(new_id())))
        if key.endswith("_at") or key.endswith("_time"):
            layout.addWidget(button("Now UTC", lambda: self.set_text_value(now())))
        self.state.currentTextChanged.connect(self.state_changed)
        self.state_changed(emit=False)
        self.setToolTip(key)

    def state_changed(self, *args, emit=True):
        self.editor.setEnabled(self.state.currentText() == "Value")
        if emit:
            self.touched = True
            self.changed.emit()

    def on_change(self, *_):
        self.touched = True
        self.changed.emit()

    def set_text_value(self, text):
        self.editor.setText(text)
        self.state.setCurrentText("Value")

    def value(self):
        if not self.touched:
            return self.original if self.original is MISSING else snapshot(self.original)
        state = self.state.currentText()
        if state == "Null":
            return None
        if state == "Omitted":
            return MISSING
        text = self.editor.toPlainText() if isinstance(self.editor, QPlainTextEdit) else (self.editor.currentText() if isinstance(self.editor, QComboBox) else self.editor.text())
        if self.typ is int:
            if not re.fullmatch(r"-?\d+", text):
                raise ValueError("Enter an integer (no 32-bit limit)")
            return int(text)
        if self.typ is bool:
            return text == "true"
        if self.typ in (dict, list):
            if len(text) > 32768:
                raise ValueError("Object editor limit is 32 KiB")
            obj = json.loads(text)
            if not isinstance(obj, self.typ):
                raise ValueError(f"Expected a JSON {self.typ.__name__}")
            return obj
        return text


class PayloadForm(QWidget):
    changed = Signal()

    def __init__(self, payload, sample):
        super().__init__()
        self.original = snapshot(payload)
        self.fields, self.object_states = {}, {}
        self.object_touched = set()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(3, 3, 12, 3)
        groups = {name: {} for name in ("Identity", "Business Details", "Provider / Outcome", "Event Metadata")}
        for key, val in sample.items():
            group = "Identity" if key.endswith("_id") or key == "order_reference" else "Business Details"
            if key in ("schema_version", "event_type", "event_time", "emitted_at", "source", "update_source"):
                group = "Event Metadata"
            elif key.startswith(("provider", "processor")) or key in ("status", "decline", "failure", "retry", "action", "error", "authorization_code"):
                group = "Provider / Outcome"
            groups[group][key] = val
        for name, fields in groups.items():
            if fields:
                box = QGroupBox(name)
                form = QFormLayout(box)
                form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
                self.build(form, fields, payload, ())
                self.layout.addWidget(box)
        self.layout.addStretch()

    def build(self, form, sample, actual, prefix):
        actual = actual if isinstance(actual, dict) else {}
        for key, exemplar in sample.items():
            path = prefix + (key,)
            value = actual.get(key, MISSING)
            if isinstance(exemplar, dict):
                box = QGroupBox(key)
                child_form = QFormLayout(box)
                state = QComboBox()
                state.addItems(["Value", "Null", "Omitted"])
                state.setCurrentText("Omitted" if value is MISSING else "Null" if value is None else "Value")
                child_form.addRow("Presence", state)
                self.object_states[path] = state
                self.build(child_form, exemplar, value, path)
                state.currentTextChanged.connect(lambda _, p=path: self.object_changed(p))
                form.addRow(box)
            else:
                field = Field(key, value, exemplar)
                self.fields[path] = field
                field.changed.connect(self.changed)
                form.addRow(key.replace("_", " ").capitalize(), field)

    def object_changed(self, path):
        self.object_touched.add(path)
        self.changed.emit()

    def payload(self):
        result = snapshot(self.original)
        errors = []
        for path, field in self.fields.items():
            field.error.clear()
            # A hidden/null object retains its child draft without writing it.
            if any(self.object_states[p].currentText() != "Value" for p in self.object_states if path[:len(p)] == p):
                continue
            # Preserve deliberately malformed raw objects until that object is edited.
            blocked = False
            for ancestor in self.object_states:
                if path[:len(ancestor)] != ancestor:
                    continue
                original = self.original
                for part in ancestor:
                    original = original.get(part, MISSING) if isinstance(original, dict) else MISSING
                edited = ancestor in self.object_touched or any(f.touched for p, f in self.fields.items() if p[:len(ancestor)] == ancestor)
                if original is not MISSING and original is not None and not isinstance(original, dict) and not edited:
                    blocked = True
            if blocked:
                continue
            try:
                value = field.value()
            except (ValueError, RecursionError) as exc:
                field.error.setText(str(exc))
                errors.append(".".join(path) + ": " + str(exc))
                continue
            obj = result
            for part in path[:-1]:
                if not isinstance(obj.get(part), dict):
                    obj[part] = {}
                obj = obj[part]
            if value is MISSING:
                obj.pop(path[-1], None)
            else:
                obj[path[-1]] = value
        for path, state in sorted(self.object_states.items(), key=lambda item: len(item[0]), reverse=True):
            obj = result
            for part in path[:-1]:
                if not isinstance(obj.get(part), dict):
                    obj[part] = {}
                obj = obj[part]
            if state.currentText() == "Null":
                obj[path[-1]] = None
            elif state.currentText() == "Omitted":
                obj.pop(path[-1], None)
        b = result.get("data", result)
        if not isinstance(b, dict):
            b = {}
        for path, field in self.fields.items():
            if hasattr(field, "equivalent"):
                try:
                    field.equivalent.setText(money(field.value(), b.get("currency", "")))
                except ValueError:
                    field.equivalent.setText("Invalid integer")
        return result, errors

    def show_issues(self, issues):
        for path, field in self.fields.items():
            messages = [i.split(": ", 1)[-1] for i in issues if i.startswith(".".join(path) + ":")]
            if messages:
                field.error.setText("; ".join(messages))


class RecordsModel(QAbstractTableModel):
    def __init__(self, columns, records=None, editable=False):
        super().__init__()
        self.columns, self.records = columns, records or []
        self.editable, self.modified = editable, set()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.columns[section][0] if orientation == Qt.Horizontal else str(section + 1) + (" *" if section in self.modified else "")
        if role == Qt.ToolTipRole and orientation == Qt.Horizontal:
            return self.columns[section][2] if len(self.columns[section]) > 2 else self.columns[section][0]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        key = self.columns[index.column()][1]
        rec = self.records[index.row()]
        value = key(rec) if callable(key) else rec.get(key)
        if role in (Qt.DisplayRole, Qt.EditRole, Qt.ToolTipRole):
            return "<null>" if value is None else json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value)
        if role == Qt.UserRole:
            return value if type(value) in (int, float) else str(value)
        if role == Qt.BackgroundRole and index.row() in self.modified:
            return QColor("#fff4d6")

    def flags(self, index):
        flags = super().flags(index)
        if self.editable:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if self.editable and role == Qt.EditRole:
            self.records[index.row()][self.columns[index.column()][1]] = None if value == "<null>" else value
            self.modified.add(index.row())
            self.dataChanged.emit(index, index)
            self.headerDataChanged.emit(Qt.Vertical, index.row(), index.row())
            return True
        return False

    def refresh(self, records=None):
        self.beginResetModel()
        if records is not None:
            self.records = records
        self.endResetModel()


class RecordTable(QTableView):
    def __init__(self, model):
        super().__init__()
        self.source = model
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setSortRole(Qt.UserRole)
        self.setModel(self.proxy)
        self.setSortingEnabled(True)
        self.sortByColumn(-1, Qt.AscendingOrder)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setDefaultSectionSize(34)
        self.horizontalHeader().setStretchLastSection(True)
        self.setMinimumHeight(150)
        model.modelReset.connect(self.size_columns)
        self.size_columns()

    def size_columns(self):
        metrics = self.fontMetrics()
        for i, column in enumerate(self.source.columns):
            width = metrics.horizontalAdvance(column[0]) + 36
            for rec in self.source.records[:20]:
                key = column[1]
                value = key(rec) if callable(key) else rec.get(key)
                width = max(width, min(240, metrics.horizontalAdvance(str(value)) + 24))
            self.setColumnWidth(i, max(100, width))

    def selected_rows(self):
        return sorted({self.proxy.mapToSource(i).row() for i in self.selectionModel().selectedRows()})


class DirectoryInput(QWidget):
    def __init__(self, value="output"):
        super().__init__()
        self.edit = QLineEdit(value)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit)
        layout.addWidget(button("Browse…", self.browse))

    def browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select future output directory")
        if path:
            self.edit.setText(path)


class ConfigDialog(QDialog):
    def __init__(self, title, defaults, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 550)
        layout = QVBoxLayout(self)
        layout.addWidget(note("Local demo configuration. No files, credentials, or network operations are performed."))
        self.form = PayloadForm(defaults, defaults)
        layout.addWidget(scroll(self.form))
        self.message = note("")
        layout.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def submit(self):
        self.value, errors = self.form.payload()
        if errors:
            self.message.setText("; ".join(errors))
        else:
            self.accept()
