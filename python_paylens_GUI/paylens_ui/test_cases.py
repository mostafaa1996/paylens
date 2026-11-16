"""Workbook-backed case catalog and independent, editable scenario snapshots."""
import json
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QAbstractItemView

from .domain import new_id, snapshot
from .widgets import RecordsModel, RecordTable


def stack_items(case):
    """Display the generated payloads already stored in the case's step objects."""
    group = new_id("case_run")
    items = []
    for step in case.TestSteps:
        payload = json.loads(step.payload or "null") if isinstance(step.payload, str) or step.payload is None else snapshot(step.payload)
        items.append(dict(
            payload=payload or {},
            step=int(step.step),
            dispatch_seconds=float(step.DispatchEvent),
            action=step.Event,
            merchant=snapshot(case.merchant), terminal_id=case.terminal_id,
            token=new_id("item"), case_run=group,
        ))
    return items


class TestCasesPage(QWidget):
    case_selected = Signal(object)

    def __init__(self, cases):
        super().__init__()
        self.cases = cases
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = RecordsModel([
            ("Case ID", lambda case: case.CaseID), ("Transaction journey", lambda case: case.TransactionTestType),
            ("Description", lambda case: case.TransactionDesc),
            ("Expected", lambda case: case.TranscationExpectedResult), ("Num of Steps", lambda case: case.TransactionStepsNumber),
        ], cases)
        self.table = RecordTable(self.model)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(100)
        self.table.horizontalHeader().setStretchLastSection(False)
        for index, width in enumerate((110, 270, 330, 510, 120)):
            self.table.setColumnWidth(index, width)
        self.table.clicked.connect(self.choose)
        layout.addWidget(self.table)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available = max(420, self.table.viewport().width() - 230)
        for index, width in enumerate((100, int(available * .25), int(available * .30), int(available * .45), 130)):
            self.table.setColumnWidth(index, width)
        self.table.resizeRowsToContents()

    def choose(self, index):
        source = self.table.proxy.mapToSource(index)
        self.case_selected.emit(self.model.records[source.row()])
