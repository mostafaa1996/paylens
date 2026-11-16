import json
import math

from PySide6.QtCore import Qt, Signal
from utils.payload_fields import get_path, set_path
from .widgets import RecordsModel


class StackModel(RecordsModel):
    edited = Signal()
    error = Signal(str)

    def __init__(self, records):
        super().__init__([], records, editable=True)
        self.busy = False
        self.refresh(records)

    def refresh(self, records=None):
        records = self.records if records is None else records
        paths = []

        def walk(payload, prefix=""):
            for key, value in payload.items():
                path = prefix + key
                if isinstance(value, dict) and value:
                    walk(value, path + ".")
                elif path not in paths:
                    paths.append(path)

        for record in records:
            walk(record["payload"])
        preferred = ["event_type", "event_id", "source", "status", "payment_id", "attempt_id", "merchant_id"]
        paths = [path for path in preferred if path in paths] + [path for path in paths if path not in preferred]
        self.beginResetModel()
        self.columns = [("Step", "step"), ("Dispatch T+ seconds", "dispatch_seconds"),
                        ("Action", "action")]
        self.columns += [(path, lambda record, path=path: get_path(record["payload"], path)) for path in paths]
        self.paths = paths
        self.records = records
        self.endResetModel()

    def flags(self, index):
        flags = super().flags(index) & ~Qt.ItemIsEditable
        if index.isValid() and not self.busy and index.column() >= 1:
            flags |= Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid() or not self.flags(index) & Qt.ItemIsEditable:
            return False
        record = self.records[index.row()]
        text = str(value)
        try:
            if index.column() == 1:
                parsed = float(text)
                if not math.isfinite(parsed) or parsed < 0:
                    raise ValueError("Timing must be a finite, non-negative number")
                record['dispatch_seconds'] = parsed
            elif index.column() == 2:
                record['action'] = text
            else:
                path = self.paths[index.column() - 3]
                old = get_path(record["payload"], path)
                if text == "<null>":
                    parsed = None
                elif isinstance(old, (dict, list, bool)):
                    parsed = json.loads(text)
                elif type(old) is int or path.endswith("_minor") or path in ("schema_version", "fulfillment_version"):
                    parsed = int(text)
                elif type(old) is float:
                    parsed = float(text)
                else:
                    parsed = text
                set_path(record["payload"], path, parsed)
        except (TypeError, ValueError) as exc:
            self.error.emit(f"Could not apply cell value: {exc}")
            return False
        self.dataChanged.emit(index, index)
        self.edited.emit()
        return True
