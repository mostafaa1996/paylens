import json
from PySide6.QtCore import QThread
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QButtonGroup, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QFileDialog)
from pathlib import Path
from .domain import snapshot
from .services import IntegrationHooks, EventHubDispatchWorker, NormalStreamWorker, CasePreparationWorker, TerminalListWorker
from .widgets import button, note, DirectoryInput, JsonView
from .theme import THEME, ensure_fonts
from .settings import SettingsPage
from .test_cases import TestCasesPage, stack_items
from Transaction_TestCases.TestCasesFromExcelReader import TestCasesFromExcelReader
from Transaction_TestCases.TestCaseClass import TestCaseClass
from .events import StackPage, HistoryPage
from .batch import BatchPage
from config import load_settings


class MainWindow(QMainWindow):
    PAGE_NAMES = ["Test Cases", "Event Stack", "Batch Files", "Event History", "Settings"]

    def __init__(self):
        super().__init__()
        ensure_fonts()
        self.setWindowTitle("PayLens Simulator")
        self.resize(1440, 900)
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(THEME)
        self.hooks = IntegrationHooks()
        self.hooks.export_dialog = self.export_dialog
        self.dispatch_running = False
        self.dispatch_thread = None
        self.dispatch_worker = None
        self.stream_thread = None
        self.stream_worker = None
        self.preparation_thread = None
        self.preparation_worker = None
        self._terminal_threads = {}
        self._preparing_case = None
        self._test_steps = []
        self._close_when_dispatch_finishes = False
        self.settings = SettingsPage()
        catalog_error = None
        try:
            reader = TestCasesFromExcelReader(Path(__file__).resolve().parents[1] / "Transactions_TestCases.xlsx")
            reader.read_test_cases()
            reader.read_test_steps()
            self._test_steps = reader.TestStepsPerTestCase
            cases = [TestCaseClass(
                record, record['Case ID'], [],
            ) for record in reader.TestCases if record.get('Case ID')]
        except Exception as exc:
            cases = []
            catalog_error = f"Could not load Transactions_TestCases.xlsx: {exc}"
        self.test_cases = TestCasesPage(cases)
        if catalog_error:
            self.test_cases.table.setToolTip(catalog_error)
        self.stack = StackPage(self.hooks)
        self.history = HistoryPage()
        self.batch = BatchPage(self.hooks)
        self.pages = QStackedWidget()
        for page in (self.test_cases, self.stack, self.batch, self.history, self.settings):
            self.pages.addWidget(page)
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(205)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 12, 0, 18)
        brand = QLabel("PayLens")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        sl.addSpacing(30)
        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        for i, name in enumerate(self.PAGE_NAMES):
            nav = button(name, lambda checked=False, index=i: self.navigate(index))
            nav.setCheckable(True)
            self.nav.addButton(nav, i)
            sl.addWidget(nav)
        self.nav.button(0).setChecked(True)
        sl.addStretch()
        layout.addWidget(sidebar)
        workspace = QWidget()
        wl = QVBoxLayout(workspace)
        wl.setContentsMargins(22, 18, 22, 12)
        wl.setSpacing(12)
        self.title = QLabel("Test Cases")
        self.title.setObjectName("pageTitle")
        wl.addWidget(self.title)
        wl.addWidget(self.pages, 1)
        layout.addWidget(workspace, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Event Hubs dispatch - delivery status reported per event")
        self.hooks.feedback.connect(self.feedback)
        self.test_cases.case_selected.connect(self.add_case)
        self.stack.dispatch_requested.connect(self.start_dispatch)
        self.stack.edit_requested.connect(self.edit_stack)
        self.stack.export_requested.connect(self.export_stack_json)
        self.stack.stream_requested.connect(self.toggle_stream)
        self.settings.changed.connect(self.apply_settings)
        self.stack.merchant.currentIndexChanged.connect(self.refresh_terminals)
        self.refresh_terminals()
        if catalog_error:
            self.feedback(catalog_error)

    def refresh_terminals(self, *_):
        merchant_id = self.stack.merchant.currentData()
        self.stack.terminal.clear()
        self.stack.terminal.addItem('Online', 'online')
        self.stack.terminal.setEnabled(False)
        self.stack.terminal.setToolTip('Loading terminals from the database...')
        thread = QThread(self)
        thread.setObjectName('TerminalListThread')
        worker = TerminalListWorker(merchant_id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.loaded.connect(self.terminals_loaded)
        worker.failed.connect(self.terminals_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.terminals_finished)
        thread.finished.connect(thread.deleteLater)
        self._terminal_threads[thread] = worker
        thread.start()

    def terminals_loaded(self, merchant_id, terminals):
        if merchant_id != self.stack.merchant.currentData():
            return
        self.stack.terminal.clear()
        self.stack.terminal.addItem('Online', 'online')
        for terminal_id, location in terminals:
            label = f'{terminal_id} — {location}' if location else str(terminal_id)
            self.stack.terminal.addItem(label, terminal_id)
        self.stack.terminal.setEnabled(True)
        self.stack.terminal.setToolTip('Applies to authorization requests in the next selected case or new stream.')

    def terminals_failed(self, merchant_id, error):
        if merchant_id == self.stack.merchant.currentData():
            self.stack.terminal.setEnabled(True)
            self.stack.terminal.setToolTip(f'Could not load terminals: {error}')
            self.feedback(f'Could not load terminals for merchant {merchant_id}: {error}. Online remains available.')

    def terminals_finished(self):
        self._terminal_threads.pop(self.sender(), None)
        if (self._close_when_dispatch_finishes and not self._terminal_threads
                and not self.dispatch_running and self.stream_thread is None
                and self.preparation_thread is None):
            self.close()

    def feedback(self, message):
        self.statusBar().showMessage(message)

    def navigate(self, index):
        self.pages.setCurrentIndex(index)
        self.nav.button(index).setChecked(True)
        self.title.setText(self.PAGE_NAMES[index])

    def add_case(self, case):
        if self.dispatch_running or self.preparation_thread is not None:
            self.feedback("Wait for the current stack operation to finish before selecting another case.")
            return
        thread = QThread(self)
        thread.setObjectName('CasePreparationThread')
        worker = CasePreparationWorker(case, self._test_steps, self.stack.merchant.currentData(),
                                       terminal_id=self.stack.terminal.currentData())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.prepared.connect(self.case_prepared)
        worker.failed.connect(self.feedback)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.preparation_finished)
        thread.finished.connect(thread.deleteLater)
        self._preparing_case = case
        self.preparation_thread, self.preparation_worker = thread, worker
        self.test_cases.table.setEnabled(False)
        self.stack.send_button.setEnabled(False)
        self.feedback(f'Preparing {case.CaseID} for {self.stack.merchant.currentText()}...')
        thread.start()

    def case_prepared(self, prepared):
        if self._close_when_dispatch_finishes:
            return
        case = self._preparing_case
        case.TestSteps = prepared.TestSteps
        case.PreviousDispatchPayloads = prepared.PreviousDispatchPayloads
        case.merchant = prepared.merchant
        case.terminal_id = prepared.terminal_id
        items = stack_items(case)
        if items:
            self.stack.cases[items[0]['case_run']] = snapshot(case)
        for item in items:
            self.stack.add(item)
        self.navigate(1)
        if items:
            index = self.stack.table.proxy.mapFromSource(self.stack.model.index(len(self.stack.items) - len(items), 0))
            self.stack.table.selectRow(index.row())
        self.feedback(f"Added {case.CaseID} with {len(items)} generated steps. Double-click a table cell to edit.")

    def preparation_finished(self):
        self.preparation_thread = None
        self.preparation_worker = None
        self._preparing_case = None
        self.test_cases.table.setEnabled(True)
        self.stack.send_button.setEnabled(not self.dispatch_running)
        if self._close_when_dispatch_finishes and not self.dispatch_running and self.stream_thread is None:
            self.close()

    def edit_stack(self, item):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit selected event JSON")
        dialog.resize(850, 650)
        layout = QVBoxLayout(dialog)
        editor = JsonView(False)
        editor.set_payload(item["payload"])
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        def save():
            try:
                payload = json.loads(editor.toPlainText())
                if not isinstance(payload, dict):
                    raise ValueError("The event must be a JSON object")
            except ValueError as exc:
                QMessageBox.warning(dialog, "Invalid JSON", str(exc))
                return
            self.stack.update_payload(item['token'], payload)
            self.stack.preview.set_payload(payload)
            dialog.accept()

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def export_stack_json(self, payloads, stack_id):
        output_dir = Path(self.settings.values()["output_dir"]).expanduser()
        suggested_path = output_dir / f"event_stack_{stack_id}.json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export all stack events", str(suggested_path), "JSON files (*.json)"
        )
        if not filename:
            return
        target = Path(filename)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payloads, ensure_ascii=False, indent=self.settings.values()["json_indent"]) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", f"Could not write the JSON file:\n{exc}")
            return
        self.feedback(f"Exported {len(payloads)} event(s) to {target}")

    def start_dispatch(self, items):
        if self.preparation_thread is not None:
            self.feedback('Wait for case preparation to finish before sending the stack.')
            return
        if self.dispatch_running:
            self.feedback("An Event Hubs dispatch is already running.")
            return
        if not items:
            self.feedback("There are no events to publish.")
            return

        invalid = []
        for index, item in enumerate(items, start=1):
            payload = item.get("payload")
            if not isinstance(payload, dict):
                invalid.append(f"item {index}: payload must be a JSON object")
        if invalid:
            QMessageBox.warning(self, "Event Hubs publish blocked", "Each payload must be a JSON object:\n" + "\n".join(invalid))
            return

        try:
            load_settings()
        except (OSError, ValueError) as exc:
            self.feedback(f"Event Hubs configuration error: {exc}")
            return

        planned = snapshot(items)

        self.dispatch_running = True
        self.stack.set_running(True)
        total_events = sum(item['action'] != 'CLOCK' for item in planned)
        self.stack.progress.setRange(0, max(total_events, 1))
        self.stack.progress.setValue(0)
        self.stack.progress.setFormat(f"Sent 0/{total_events} events")
        thread = QThread(self)
        thread.setObjectName("EventHubDispatchThread")
        worker = EventHubDispatchWorker(planned, self.stack.cases, merchant_id=self.stack.merchant.currentData())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.item_updated.connect(self.item_updated)
        worker.feedback.connect(self.feedback)
        worker.progress.connect(self.progress)
        worker.finished.connect(self.completed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.dispatch_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self.dispatch_thread, self.dispatch_worker = thread, worker
        self.feedback(f"Publishing {len(planned)} event(s) to Event Hubs. Each event is counted after the sender returns successfully.")
        thread.start()

    def item_updated(self, item):
        self.stack.update_item(item)
        if item.get("outcome") in ("accepted", "failed", "checkpoint"):
            self.history.record(item)
            if item.get("outcome") == "accepted":
                self.feedback(f"Sent event {item['payload'].get('event_id')} to Event Hubs. Consumer processing is separate.")
            elif item['outcome'] == 'checkpoint':
                self.feedback(f"Observation checkpoint reached: {item['case_id']}, step {item['step']}.")
            else:
                self.feedback(f"Event Hubs publish failed for {item['payload'].get('event_id')}: {item.get('transport_error', 'delivery was not confirmed')}.")

    def progress(self, completed, total):
        self.stack.progress.setRange(0, max(total, 1))
        self.stack.progress.setValue(completed)
        self.stack.progress.setFormat(f"Sent {completed}/{total} events")

    def completed(self, results):
        accepted = sum(r["outcome"] == "accepted" for r in results)
        failed = sum(r["outcome"] == "failed" and r['action'] != 'CLOCK' for r in results)
        total = sum(r['action'] != 'CLOCK' for r in results)
        self.progress(accepted, total)
        if failed:
            self.stack.progress.setFormat(f"Sent {accepted}/{total} events | {failed} failed")
        self.feedback(f"Event Hubs dispatch finished: {accepted} events sent, {failed} failed. Successful sending does not confirm consumer processing.")

    def dispatch_thread_finished(self):
        self.dispatch_running = False
        self.dispatch_worker = None
        self.dispatch_thread = None
        self.stack.set_running(False)
        if self._close_when_dispatch_finishes and self.stream_thread is None and self.preparation_thread is None:
            self.close()

    def toggle_stream(self, interval):
        if self.stream_thread is not None:
            self.stream_worker.stop()
            self.stack.set_streaming(True, stopping=True)
            return
        if not self.test_cases.cases:
            self.feedback("No test cases are available for streaming.")
            return
        try:
            load_settings()
        except (OSError, ValueError) as exc:
            self.feedback(f"Event Hubs configuration error: {exc}")
            return
        thread = QThread(self)
        thread.setObjectName("NormalCaseStreamThread")
        worker = NormalStreamWorker(self.test_cases.cases[0], interval, self._test_steps,
                                    merchant_id=self.stack.merchant.currentData(),
                                    terminal_id=self.stack.terminal.currentData())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.item_updated.connect(self.stream_item_updated)
        worker.feedback.connect(self.feedback)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self.stream_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self.stream_thread, self.stream_worker = thread, worker
        self.stack.set_streaming(True)
        self.feedback(f"Streaming {self.test_cases.cases[0].CaseID} every {interval:g} seconds. Stack sending remains available.")
        thread.start()

    def stream_item_updated(self, item):
        self.history.record(item)
        self.stack.stream_status.setText(f"Stream: {item['payload'].get('event_type') or item.get('action', 'Event')} — {item['outcome']}")

    def stream_thread_finished(self):
        self.stream_thread = None
        self.stream_worker = None
        self.stack.set_streaming(False)
        if self._close_when_dispatch_finishes and not self.dispatch_running and self.preparation_thread is None:
            self.close()

    def apply_settings(self):
        values = self.settings.values()
        self.batch.apply_settings(values)
        self.feedback("Session preferences applied. Event Hubs connection settings are read from .env when sending.")

    def export_dialog(self, kind, selection, options=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Export request • SIMULATED")
        dialog.resize(620, 300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(note(f"{kind} • {len(selection)} item(s). This invokes a future export hook. No files will be saved."))
        form = QFormLayout()
        directory = DirectoryInput(self.settings.values()["output_dir"])
        filename = QLineEdit("<dataset>_<date>.csv")
        form.addRow("Output directory", directory)
        form.addRow("Filename pattern preview", filename)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            opts = snapshot(options or {})
            opts.update(output_directory=directory.edit.text(), filename_pattern=filename.text(), json_indent=self.settings.values()["json_indent"])
            self.hooks.request_export.emit(kind, snapshot(selection), opts)

    def closeEvent(self, event):
        if self._terminal_threads and not (self.dispatch_running or self.stream_thread is not None or self.preparation_thread is not None):
            self._close_when_dispatch_finishes = True
            event.ignore()
            return
        if self.dispatch_running or self.stream_thread is not None or self.preparation_thread is not None:
            if QMessageBox.question(self, "Event Hubs publish in progress", "Stop starting new stream cases and close after case preparation, the stack, and active cases finish?") != QMessageBox.Yes:
                event.ignore()
                return
            self._close_when_dispatch_finishes = True
            if self.stream_worker is not None:
                self.stream_worker.stop()
                self.stack.set_streaming(True, stopping=True)
            event.ignore()
            return
        if self.stack.items and not self._close_when_dispatch_finishes:
            if QMessageBox.question(self, "Close local workspace?", "Drafts, stack, history, and preferences are held in memory. Close and discard session state?") != QMessageBox.Yes:
                event.ignore()
                return
        event.accept()
