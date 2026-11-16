import json
import re
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QStyle,
    QPlainTextEdit, QLineEdit, QScrollArea,
    QTableView, QAbstractItemView, QFileDialog)


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
