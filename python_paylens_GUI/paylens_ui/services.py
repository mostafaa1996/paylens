"""Integration signals and Event Hubs work that stays off the Qt UI thread."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot
from .domain import snapshot, now
from Transaction_TestCases.TestCaseClass import TestCaseClass
from Transactions_tests.select_merchant import select_merchant
from utils.Sql_interface import create_sql_connection
from utils.EventHubs_interface import create_event_hub_producer, send_event_hubs_message


def _merchant_for_run(merchant, merchant_id):
    if merchant is not None:
        return merchant
    cursor = create_sql_connection()
    connection = cursor.connection
    try:
        merchant = select_merchant(cursor, merchant_id)
        if merchant is None:
            raise ValueError(f'Merchant {merchant_id} was not found')
        # pyodbc.Row cannot be deep-copied with the case/stack snapshots.
        return merchant if isinstance(merchant, dict) else {'merchant_id': merchant.merchant_id}
    finally:
        try:
            cursor.close()
        finally:
            connection.close()


def _create_case(source, step_rows, merchant_id, terminal_id=None):
    merchant = _merchant_for_run(None, merchant_id)
    details = {'Case ID': source.CaseID, 'Transaction journey': source.TransactionTestType,
               'Why required': source.TransactionDesc,
               'Expected result and reporting purpose': source.TranscationExpectedResult,
               'Steps': source.TransactionStepsNumber}
    return TestCaseClass(details, source.CaseID, step_rows,
                         merchant=merchant, terminal_id=terminal_id)


def load_terminals(merchant_id):
    cursor = create_sql_connection()
    connection = cursor.connection
    try:
        cursor.execute('SELECT terminal_id, location_name FROM terminal_machines '
                       'WHERE merchant_id = ? ORDER BY terminal_id', merchant_id)
        return [(row.terminal_id, row.location_name) for row in cursor.fetchall()]
    finally:
        try:
            cursor.close()
        finally:
            connection.close()


class TerminalListWorker(QObject):
    loaded = Signal(int, object)
    failed = Signal(int, str)
    finished = Signal()

    def __init__(self, merchant_id):
        super().__init__()
        self.merchant_id = int(merchant_id)

    @Slot()
    def run(self):
        try:
            self.loaded.emit(self.merchant_id, load_terminals(self.merchant_id))
        except Exception as exc:
            self.failed.emit(self.merchant_id, str(exc))
        finally:
            self.finished.emit()


class CasePreparationWorker(QObject):
    """Create only the selected case's steps, using its captured merchant."""

    prepared = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, case, step_rows, merchant_id, terminal_id=None):
        super().__init__()
        self.case = snapshot(case)
        self.step_rows = snapshot(step_rows)
        self.merchant_id = int(merchant_id)
        self.terminal_id = terminal_id

    @Slot()
    def run(self):
        try:
            self.prepared.emit(_create_case(self.case, self.step_rows, self.merchant_id, self.terminal_id))
        except Exception as exc:
            self.failed.emit(f'Could not prepare {self.case.CaseID}: {exc}')
        finally:
            self.finished.emit()


class IntegrationHooks(QObject):
    request_generate_batch_files = Signal(object)
    request_export = Signal(str, object, object)
    feedback = Signal(str)

    def __init__(self):
        super().__init__()
        self.request_generate_batch_files.connect(
            lambda config: self.feedback.emit("SIMULATED: batch file configuration received. No external operation performed.")
        )
        self.request_export.connect(lambda kind, selection, options: self.feedback.emit(f"SIMULATED: {kind} export requested for {len(selection)} item(s). No files written."))


def _event_result(item, case_id, outcome, *, error=None, stream=False):
    """Execution results are separate snapshots; stack items keep eight fields."""
    result = snapshot(item)
    result.update(case_id=case_id, outcome=outcome, dispatched_at=now(), stream=stream)
    if error is not None:
        result['transport_error'] = str(error)
    return result


class EventHubDispatchWorker(QObject):
    """Execute edited stack items through the unchanged TestCaseClass runner."""

    item_updated = Signal(object)
    progress = Signal(int, int)
    feedback = Signal(str)
    finished = Signal(object)

    def __init__(self, items, cases, merchant_id=21):
        super().__init__()
        self.items = snapshot(items)
        self.cases = snapshot(cases)
        self.merchant_id = int(merchant_id)

    @Slot()
    def run(self):
        groups = {}
        for item in snapshot(self.items):
            groups.setdefault(item['case_run'], []).append(item)
        total = sum(item['action'] != 'CLOCK' for item in self.items)
        results = []
        sent = 0
        producer = None
        try:
            for case_run, case_items in groups.items():
                ordered_items = case_items
                source = self.cases[case_run]
                index = 0
                try:
                    original_steps = {int(step.step): step for step in source.TestSteps}
                    rows = []
                    for item in case_items:
                        original = original_steps[item['step']]
                        rows.append({
                            'Case ID': source.CaseID, 'Step': item['step'],
                            'Dispatch T+ seconds': item['dispatch_seconds'],
                            'Logical event T+ seconds': original.sourceEvent,
                            'Event / action': item['action'], 'Source': original.source,
                            'Status / check': original.status,
                            'Payload JSON': json.dumps(item['payload'], ensure_ascii=False),
                        })
                    details = {'Case ID': source.CaseID, 'Transaction journey': source.TransactionTestType,
                               'Why required': source.TransactionDesc,
                               'Expected result and reporting purpose': source.TranscationExpectedResult,
                               'Steps': len(rows)}
                    first = case_items[0]
                    case = TestCaseClass(details, source.CaseID, rows,
                        merchant=_merchant_for_run(first['merchant'], self.merchant_id),
                        terminal_id=first['terminal_id'])
                    by_step = {item['step']: item for item in case_items}
                    ordered_items = [by_step[int(step.step)] for step in case.TestSteps]

                    def send(message):
                        nonlocal index, sent, producer
                        item = ordered_items[index]
                        if item['action'] == 'CLOCK':
                            result = _event_result(item, source.CaseID, 'checkpoint')
                        else:
                            item['payload'] = json.loads(message)
                            if producer is None:
                                producer = create_event_hub_producer()
                            send_event_hubs_message(message, producer=producer)
                            result = _event_result(item, source.CaseID, 'accepted')
                            sent += 1
                        self.item_updated.emit(result)
                        results.append(result)
                        self.progress.emit(sent, total)
                        index += 1

                    case.sender = send
                    case.run_test_case()
                except Exception as exc:
                    for pending in ordered_items[index:]:
                        result = _event_result(pending, source.CaseID, 'failed', error=exc)
                        self.item_updated.emit(result)
                        results.append(result)
                        self.progress.emit(sent, total)
        finally:
            if producer is not None:
                try:
                    producer.close()
                except Exception as exc:
                    self.feedback.emit(f"Could not close the stack Event Hubs client: {exc}")
            self.finished.emit(results)


class NormalStreamWorker(QObject):
    """Run fresh original TestCaseClass instances at the requested cadence."""

    item_updated = Signal(object)
    feedback = Signal(str)
    finished = Signal()
    MAX_ACTIVE_CASES = 64

    def __init__(self, case, interval, step_rows, merchant_id=21, terminal_id=None):
        super().__init__()
        self.case = snapshot(case)
        self.step_rows = snapshot(step_rows)
        self.merchant_id = int(merchant_id)
        self.terminal_id = terminal_id
        self.interval = max(0.1, float(interval))
        self._stop = Event()

    def stop(self):
        """Stop starting new cases; active cases send all their remaining steps."""
        self._stop.set()

    def _run_case(self):
        from .test_cases import stack_items

        case = None
        items = []
        index = 0
        producer = None

        def send(message):
            nonlocal index, producer
            item = items[index]
            if item['action'] == 'CLOCK':
                result = _event_result(item, case.CaseID, 'checkpoint', stream=True)
            else:
                item['payload'] = json.loads(message)
                if producer is None:
                    producer = create_event_hub_producer()
                send_event_hubs_message(message, producer=producer)
                result = _event_result(item, case.CaseID, 'accepted', stream=True)
            self.item_updated.emit(result)
            index += 1

        try:
            case = _create_case(self.case, self.step_rows, self.merchant_id, self.terminal_id)
            items = stack_items(case)
            case.sender = send
            case.run_test_case()
        except Exception as exc:
            if index < len(items):
                item = items[index]
                self.item_updated.emit(_event_result(item, case.CaseID, 'failed', error=exc, stream=True))
            self.feedback.emit(f"Normal stream stopped: {exc}")
            self._stop.set()
        finally:
            if producer is not None:
                try:
                    producer.close()
                except Exception as exc:
                    self.feedback.emit(f"Could not close the streaming Event Hubs client: {exc}")

    @Slot()
    def run(self):
        try:
            # Each overlapping case owns its execution thread and producer.
            # The original runner owns step generation and all step delays.
            with ThreadPoolExecutor(max_workers=self.MAX_ACTIVE_CASES, thread_name_prefix='NormalCase') as pool:
                active = set()
                while not self._stop.is_set():
                    for future in list(active):
                        if future.done():
                            try:
                                future.result()
                            except Exception:
                                self._stop.set()
                                raise
                            active.remove(future)
                    if len(active) < self.MAX_ACTIVE_CASES:
                        active.add(pool.submit(self._run_case))
                    else:
                        self.feedback.emit('Normal stream is at capacity; skipping this case start.')
                    self._stop.wait(self.interval)
                # Exiting the pool waits for every active case to finish,
                # including its final capture response and client cleanup.
        except Exception as exc:
            self.feedback.emit(f"Normal stream stopped: {exc}")
        finally:
            self.finished.emit()
