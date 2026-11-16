"""Offscreen catalog/stack and concurrent Event Hubs worker checks; no real sends."""
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from paylens_ui.domain import snapshot
from paylens_ui.services import EventHubDispatchWorker, NormalStreamWorker
from paylens_ui.test_cases import stack_items
from Transaction_TestCases.TestCaseClass import TestCaseClass, TestStepClass
from Transaction_TestCases.TestCasesFromExcelReader import TestCasesFromExcelReader
from paylens_ui.window import MainWindow

app = QApplication.instance() or QApplication([])


def pump(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.002)
    if not predicate():
        raise AssertionError("Timed out waiting for background worker")


def settings():
    return SimpleNamespace(eventhub_connection_string="fake-connection")


def sql_cursor():
    cursor = Mock()
    cursor.fetchall.return_value = [SimpleNamespace(customer_id=7)]
    cursor.fetchone.return_value = SimpleNamespace(payment_token='test-token', processor_code='PROC_A', merchant_id=21)
    return cursor


class CaseUiTests(unittest.TestCase):
    def setUp(self):
        self.qt_errors = []
        exception_patch = patch('sys.excepthook', side_effect=lambda *args: self.qt_errors.append(args))
        exception_patch.start()
        self.addCleanup(exception_patch.stop)
        sql_patch = patch('Transaction_TestCases.TestCaseClass.create_sql_connection', side_effect=sql_cursor)
        self.sql_connect = sql_patch.start()
        self.addCleanup(sql_patch.stop)
        merchant_patch = patch('paylens_ui.services.create_sql_connection', side_effect=sql_cursor)
        self.merchant_connect = merchant_patch.start()
        self.addCleanup(merchant_patch.stop)
        terminal_patch = patch('paylens_ui.services.load_terminals',
                               side_effect=lambda merchant_id: [(merchant_id * 100, 'Main branch')])
        self.load_terminals = terminal_patch.start()
        self.addCleanup(terminal_patch.stop)
        self.clients = []

        def create():
            client = SimpleNamespace(owner=threading.get_ident(), closed=False)
            def close():
                self.assertEqual(client.owner, threading.get_ident())
                client.closed = True
            client.close = close
            self.clients.append(client)
            return client

        self.producer_patch = patch("paylens_ui.services.create_event_hub_producer", side_effect=create)
        self.producer_patch.start()
        self.addCleanup(self.producer_patch.stop)
        self.window = MainWindow()
        self.window.show()
        app.processEvents()
        pump(lambda: not self.window._terminal_threads)

    def tearDown(self):
        if self.window.stream_worker is not None:
            self.window.stream_worker.stop()
        pump(lambda: self.window.stream_thread is None and not self.window.dispatch_running and self.window.preparation_thread is None and not self.window._terminal_threads)
        self.window.hide()
        self.window.deleteLater()
        app.processEvents()
        self.assertEqual(self.qt_errors, [])

    def set_delays(self, case, delays):
        rows = [row for row in self.window._test_steps if row['Case ID'] == case.CaseID]
        for row, delay in zip(rows, delays):
            row['Dispatch T+ seconds'] = delay

    def select_case(self, case):
        self.window.add_case(case)
        pump(lambda: self.window.preparation_thread is None)
        self.assertTrue(case.TestSteps)

    def test_terminal_selection_is_merchant_specific_and_captured_by_case(self):
        window = self.window
        window.stack.merchant.setCurrentIndex(window.stack.merchant.findData(22))
        pump(lambda: not window._terminal_threads)
        self.assertEqual(window.stack.terminal.itemText(0), 'Online')
        self.assertEqual(window.stack.terminal.count(), 2)
        self.assertEqual(window.stack.terminal.itemData(1), 2200)
        window.stack.terminal.setCurrentIndex(1)
        self.select_case(window.test_cases.cases[0])
        request = window.stack.items[0]['payload']
        self.assertEqual(request['channel'], 'pos')
        self.assertEqual(request['terminal_id'], 2200)
        self.assertEqual(request['payment_method']['card_presence'], 'CP')
        self.assertEqual(request['payment_method']['entry_mode'], 'offline')
        self.assertIsNone(request['ip_address'])
        window.stack.terminal.setCurrentIndex(0)
        self.assertTrue(all(item['terminal_id'] == 2200 for item in window.stack.items))
        self.select_case(window.test_cases.cases[0])
        online = window.stack.items[4]['payload']
        self.assertEqual(online['channel'], 'web')
        self.assertIsNone(online['terminal_id'])
        self.assertEqual(online['payment_method']['entry_mode'], 'online')
        messages = []
        with patch('paylens_ui.window.load_settings', return_value=settings()), \
             patch('paylens_ui.services.send_event_hubs_message',
                   side_effect=lambda message, **kwargs: messages.append(json.loads(message))), \
             patch('Transaction_TestCases.TestCaseClass.time.sleep'):
            window.start_dispatch(window.stack.items)
            pump(lambda: not window.dispatch_running)
        self.assertEqual(messages[0]['terminal_id'], 2200)
        self.assertIsNone(messages[4]['terminal_id'])

    def test_stream_captures_selected_terminal(self):
        self.window.stack.terminal.setCurrentIndex(1)
        with patch('paylens_ui.window.load_settings', return_value=settings()), \
             patch.object(NormalStreamWorker, 'run', lambda worker: worker.finished.emit()):
            self.window.toggle_stream(5)
            self.assertEqual(self.window.stream_worker.terminal_id, 2100)
            self.window.stack.terminal.setCurrentIndex(0)
            self.assertEqual(self.window.stream_worker.terminal_id, 2100)
            pump(lambda: self.window.stream_thread is None)

    def test_catalog_click_and_edit_sorted_stack(self):
        window = self.window
        self.assertEqual(window.test_cases.model.rowCount(), 50)
        self.assertIs(window.test_cases.model.records[0], window.test_cases.cases[0])
        self.assertIsInstance(window.test_cases.cases[0], TestCaseClass)
        self.assertTrue(all(case.TestSteps == [] for case in window.test_cases.cases))
        self.sql_connect.assert_not_called()
        self.merchant_connect.assert_not_called()
        self.assertEqual([column[0] for column in window.test_cases.model.columns],
                         ["Case ID", "Transaction journey", "Description", "Expected", "Num of Steps"])
        window.test_cases.table.proxy.sort(0, Qt.DescendingOrder)
        displayed = window.test_cases.table.proxy.index(0, 0).data()
        window.test_cases.choose(window.test_cases.table.proxy.index(0, 0))
        pump(lambda: window.preparation_thread is None)
        self.assertEqual(window.pages.currentIndex(), 1)
        self.assertEqual(window.stack.cases[window.stack.items[0]["case_run"]].CaseID, displayed)
        window.stack.clear = lambda: None
        window.stack.items.clear()
        window.stack.refresh()
        self.select_case(window.test_cases.cases[0])
        self.assertEqual(len(window.stack.items), 4)
        model = window.stack.model
        column = 3 + model.paths.index("requested_amount_minor")
        self.assertTrue(model.setData(model.index(0, column), "12345"))
        self.assertEqual(window.stack.items[0]["payload"]["requested_amount_minor"], 12345)
        column = 3 + model.paths.index("payment_method.token")
        self.assertTrue(model.setData(model.index(0, column), "my-token"))
        self.assertEqual(window.stack.items[0]["payload"]["payment_method"]["token"], "my-token")
        self.assertTrue(model.setData(model.index(0, column), "<null>"))
        self.assertIsNone(window.stack.items[0]["payload"]["payment_method"]["token"])
        self.assertFalse(model.setData(model.index(0, 1), "nan"))
        self.assertFalse(model.setData(model.index(0, 1), "-1"))
        time_column = 3 + model.paths.index('event_time')
        model.setData(model.index(0, time_column), '2026-11-16T00:00:00.000Z')
        self.assertEqual(window.stack.items[0]['payload']['event_time'], '2026-11-16T00:00:00.000Z')
        exported = []
        window.stack.export_requested.connect(lambda payloads, _: exported.extend(payloads))
        window.stack.export_requested.disconnect(window.export_stack_json)
        window.stack.export_all()
        self.assertEqual(exported[0]["requested_amount_minor"], 12345)
        self.assertFalse(hasattr(window.stack, "resend_button"))
        self.assertFalse(hasattr(window.stack, "retry_button"))
        self.assertFalse(hasattr(window.stack, "delay"))

    def test_selection_generates_only_selected_case_with_captured_merchant_and_token(self):
        window = self.window
        first, untouched = window.test_cases.cases[:2]
        with patch('paylens_ui.services.select_merchant', side_effect=lambda cursor, merchant_id: SimpleNamespace(merchant_id=merchant_id)) as select:
            window.stack.merchant.setCurrentIndex(window.stack.merchant.findData(24))
            self.select_case(first)
            self.assertEqual(select.call_args.args[1], 24)
            self.assertEqual(untouched.TestSteps, [])
            self.assertEqual(len(first.TestSteps), 4)
            self.assertEqual(len(first.PreviousDispatchPayloads), 4)
            first_payment = window.stack.items[0]['payload']['payment_id']
            self.assertEqual(window.stack.items[0]['payload']['merchant_id'], 24)
            self.assertEqual(window.stack.items[0]['payload']['payment_method']['token'], 'test-token')
            self.assertTrue(all(item['payload']['merchant_id'] == 24 for item in window.stack.items))
            window.stack.merchant.setCurrentIndex(window.stack.merchant.findData(25))
            self.select_case(first)
            self.assertTrue(all(item['payload']['merchant_id'] == 24 for item in window.stack.items[:4]))
            self.assertTrue(all(item['payload']['merchant_id'] == 25 for item in window.stack.items[4:]))
            self.assertNotEqual(window.stack.items[4]['payload']['payment_id'], first_payment)
            self.assertIs(window.test_cases.model.records[0], first)
            self.assertEqual(self.clients, [])

    def test_failed_preparation_leaves_case_and_stack_empty(self):
        case = self.window.test_cases.cases[0]
        with patch('paylens_ui.services.select_merchant', return_value=None):
            self.window.add_case(case)
            pump(lambda: self.window.preparation_thread is None)
        self.assertEqual(case.TestSteps, [])
        self.assertEqual(self.window.stack.items, [])
        self.assertTrue(self.window.test_cases.table.isEnabled())
        self.assertTrue(self.window.stack.send_button.isEnabled())
        self.assertIn('was not found', self.window.statusBar().currentMessage())

    def test_clock_checkpoint_is_logged_without_sending_or_incrementing_event_count(self):
        case = next(case for case in self.window.test_cases.cases if case.CaseID == 'PL-0041')
        self.set_delays(case, (0, 0.005, 0.02))
        self.select_case(case)
        self.assertEqual(self.window.stack.items[-1]['action'], 'CLOCK')
        messages = []
        with patch('paylens_ui.window.load_settings', side_effect=settings), \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=lambda message, **kwargs: messages.append(json.loads(message))):
            self.window.stack.send()
            pump(lambda: not self.window.dispatch_running)
        self.assertEqual(len(messages), 2)
        self.assertEqual(self.window.stack.progress.format(), 'Sent 2/2 events')
        self.assertEqual([record['outcome'] for record in self.window.history.records],
                         ['accepted', 'accepted', 'checkpoint'])
        self.assertEqual(self.window.history.model.index(2, 3).data(), 'CLOCK')
        self.assertEqual(self.window.history.model.index(2, 5).data(), 'Observation checkpoint')

    def test_stream_clock_checkpoint_does_not_publish_a_payload(self):
        case = next(case for case in self.window.test_cases.cases if case.CaseID == 'PL-0041')
        self.set_delays(case, (0, 0, 0))
        worker = NormalStreamWorker(case, 5, self.window._test_steps)
        outcomes = []
        worker.item_updated.connect(outcomes.append)
        with patch('paylens_ui.services.send_event_hubs_message') as send:
            worker._run_case()
        self.assertEqual(send.call_count, 2)
        self.assertEqual([record['outcome'] for record in outcomes], ['accepted', 'accepted', 'checkpoint'])
        self.assertTrue(all(record['stream'] for record in outcomes))

    def test_close_waits_for_background_preparation(self):
        entered, release = threading.Event(), threading.Event()

        def select(cursor, merchant_id):
            entered.set()
            release.wait(2)
            return SimpleNamespace(merchant_id=merchant_id)

        with patch('paylens_ui.services.select_merchant', side_effect=select), \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.window.add_case(self.window.test_cases.cases[0])
            pump(entered.is_set)
            self.window.close()
            self.assertIsNotNone(self.window.preparation_thread)
            release.set()
            pump(lambda: self.window.preparation_thread is None and not self.window.isVisible())
        self.assertEqual(self.window.stack.items, [])
        self.assertEqual(self.clients, [])

    def test_parallel_stream_and_manual_send_remain_responsive(self):
        window = self.window
        case = snapshot(window.test_cases.cases[0])
        self.set_delays(case, [index * 0.01 for index in range(4)])
        window.test_cases.cases[0] = case
        producers = []

        def publish(message, *, producer):
            self.assertEqual(producer.owner, threading.get_ident())
            self.assertFalse(producer.closed)
            owner = threading.get_ident()
            producer = next((p for p in producers if p.owner == owner), None)
            if producer is None:
                producer = SimpleNamespace(owner=owner, sent=[])
                producers.append(producer)
            producer.sent.append(json.loads(message))

        with patch("paylens_ui.window.load_settings", side_effect=settings), \
             patch("paylens_ui.services.send_event_hubs_message", side_effect=publish):
            window.toggle_stream(0.1)
            pump(lambda: producers and len(producers[0].sent) >= 4)
            self.assertFalse(window.stack.busy)
            self.assertTrue(window.stack.send_button.isEnabled())
            self.select_case(case)
            self.assertEqual(len(window.stack.items), 4)
            # Keep the manual worker alive long enough to overlap another stream cycle.
            window.stack.items[-1]["dispatch_seconds"] = 0.3
            window.stack.send()
            self.assertTrue(window.dispatch_running)
            self.assertIsNotNone(window.stream_thread)
            # The worker owns an immutable copy, independent of UI drafts.
            window.stack.items[0]["payload"]["currency"] = "TEST"
            pump(lambda: len(producers) == 2 and len(producers[0].sent) >= 8)
            pump(lambda: not window.dispatch_running)
            self.assertEqual(len(producers[1].sent), 4)
            self.assertEqual(window.stack.progress.value(), 4)
            self.assertEqual(window.stack.progress.maximum(), 4)
            self.assertEqual(window.stack.progress.format(), "Sent 4/4 events")
            expected = {'payload', 'step', 'action', 'dispatch_seconds', 'token', 'case_run', 'merchant', 'terminal_id'}
            self.assertTrue(all(set(item) == expected for item in window.stack.items))
            self.assertNotEqual(producers[1].sent[0]["currency"], "TEST")
            self.assertEqual(len(window.stack.items), 4)
            self.assertNotEqual(producers[0].owner, producers[1].owner)
            self.assertGreaterEqual(len(self.clients), 2)
            first_payment = producers[0].sent[0]["payment_id"]
            second_payment = producers[0].sent[4]["payment_id"]
            self.assertNotEqual(first_payment, second_payment)
            window.toggle_stream(0.1)
            pump(lambda: window.stream_thread is None)
            self.assertEqual(window.stack.stream_button.text(), "Start normal stream")
            self.assertTrue(all(client.closed for client in self.clients))

    def test_close_stops_stream_before_destroying_threads(self):
        self.set_delays(self.window.test_cases.cases[0], [0.005] * 4)
        with patch("paylens_ui.window.load_settings", side_effect=settings), \
             patch("paylens_ui.services.send_event_hubs_message"), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            self.window.toggle_stream(5)
            pump(lambda: bool(self.window.history.records))
            self.window.close()
            pump(lambda: self.window.stream_thread is None and not self.window.isVisible())

    def test_stream_stop_finishes_the_started_case_including_capture_response(self):
        window = self.window
        self.set_delays(window.test_cases.cases[0], (0, 0.01, 0.02, 0.12))
        messages = []
        with patch('paylens_ui.window.load_settings', side_effect=settings), \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=lambda message, **kwargs: messages.append(json.loads(message))):
            window.toggle_stream(5)
            pump(lambda: len(messages) >= 1)
            window.toggle_stream(5)
            pump(lambda: window.stream_thread is None)
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[-1]['event_type'], 'capture_result')
        self.assertEqual(len({message['payment_id'] for message in messages}), 1)
        self.assertTrue(all(record['outcome'] == 'accepted' for record in window.history.records))
        self.assertTrue(all(client.closed for client in self.clients))

    def test_close_finishes_all_stack_events_before_destroying_worker(self):
        window = self.window
        self.set_delays(window.test_cases.cases[0], (0, 0.01, 0.02, 0.12))
        self.select_case(window.test_cases.cases[0])
        messages = []
        with patch('paylens_ui.window.load_settings', side_effect=settings), \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=lambda message, **kwargs: messages.append(json.loads(message))), \
             patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            window.stack.send()
            pump(lambda: len(messages) >= 1)
            window.close()
            pump(lambda: not window.dispatch_running and not window.isVisible())
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[-1]['event_type'], 'capture_result')
        self.assertEqual(window.stack.progress.format(), 'Sent 4/4 events')
        self.assertTrue(all(client.closed for client in self.clients))

    def test_merchant_selection_is_used_and_frozen_for_each_run(self):
        window = self.window
        combo = window.stack.merchant
        self.assertEqual([combo.itemText(i) for i in range(combo.count())], [
            'Nile Electronics (21)', 'Alex Fashion (22)', 'Delta Market (23)',
            'Cairo Home (24)', 'Red Sea Sports (25)',
        ])
        self.set_delays(window.test_cases.cases[0], [0] * 4)
        messages = []

        def send(message, *, producer):
            messages.append(json.loads(message))

        with patch('paylens_ui.window.load_settings', side_effect=settings), \
             patch('paylens_ui.services.select_merchant', side_effect=lambda cursor, merchant_id: SimpleNamespace(merchant_id=merchant_id)) as select, \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=send):
            combo.setCurrentIndex(combo.findData(24))
            self.select_case(window.test_cases.cases[0])
            window.stack.send()
            combo.setCurrentIndex(combo.findData(25))
            pump(lambda: not window.dispatch_running)
            self.assertEqual(len(messages), 4)
            self.assertTrue(all(message['merchant_id'] == 24 for message in messages))
            self.assertEqual(select.call_args_list[0].args[1], 24)

            window.toggle_stream(5)
            combo.setCurrentIndex(combo.findData(22))
            pump(lambda: len(messages) >= 8)
            window.toggle_stream(5)
            pump(lambda: window.stream_thread is None)
            self.assertTrue(all(message['merchant_id'] == 25 for message in messages[4:]))
            self.assertEqual(select.call_args_list[1].args[1], 25)

    def test_dispatch_allows_test_values_and_still_blocks_non_object_payloads(self):
        window = self.window
        self.set_delays(window.test_cases.cases[0], [0] * 4)
        self.select_case(window.test_cases.cases[0])
        window.stack.items[0]['payload']['requested_amount_minor'] = -1
        messages = []
        with patch('paylens_ui.window.load_settings', side_effect=settings), \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=lambda message, **kwargs: messages.append(json.loads(message))):
            window.stack.send()
            pump(lambda: not window.dispatch_running)
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]['requested_amount_minor'], -1)
        with patch.object(QMessageBox, 'warning') as warning, \
             patch('paylens_ui.window.EventHubDispatchWorker') as worker:
            window.start_dispatch([{'payload': ['invalid']}])
        warning.assert_called_once()
        worker.assert_not_called()

    def test_stream_starts_overlapping_cases_at_interval(self):
        case = snapshot(self.window.test_cases.cases[0])
        self.set_delays(case, (0, 0.01, 0.02, 0.25))
        worker = NormalStreamWorker(case, 0.1, self.window._test_steps)
        sent = []

        def publish(message, *, producer):
            payload = json.loads(message)
            sent.append((payload["event_type"], payload["payment_id"], time.monotonic()))
            if len(sent) >= 10:
                worker.stop()

        with patch("paylens_ui.services.send_event_hubs_message", side_effect=publish):
            worker.run()
        first_payment = sent[0][1]
        first_capture = next(index for index, row in enumerate(sent) if row[0] == "capture_result")
        requests = [row for row in sent if row[0] == "authorization_requested"]
        self.assertGreaterEqual(len(requests), 3)
        self.assertNotEqual(requests[0][1], requests[1][1])
        self.assertLess(next(index for index, row in enumerate(sent) if row[1] != first_payment), first_capture)
        self.assertGreaterEqual(requests[1][2] - requests[0][2], 0.08)

    def test_stream_failure_reports_error_and_stops(self):
        worker = NormalStreamWorker(self.window.test_cases.cases[0], 5, self.window._test_steps)
        errors, outcomes, finished = [], [], []
        worker.feedback.connect(errors.append)
        worker.item_updated.connect(outcomes.append)
        worker.finished.connect(lambda: finished.append(True))

        def publish(message, *, producer):
            raise RuntimeError("Event Hubs rejected message")

        with patch("paylens_ui.services.send_event_hubs_message", side_effect=publish):
            worker.run()
        app.processEvents()
        self.assertEqual(outcomes[0]["outcome"], "failed")
        self.assertIn("Event Hubs rejected message", errors[0])
        self.assertEqual(finished, [True])
        self.assertTrue(self.clients[0].closed)

    def test_current_pages_settings_batch_edits_and_history_still_work(self):
        window = self.window
        for index in range(window.pages.count()):
            window.navigate(index)
            app.processEvents()
            self.assertTrue(window.pages.currentWidget().isVisible())
            self.assertEqual(window.title.text(), window.PAGE_NAMES[index])

        window.settings.output_dir.edit.setText('test-output')
        window.settings.json_indent.setCurrentIndex(1)
        window.settings.csv_null.setText('NULL')
        window.apply_settings()
        config = window.batch.config(all_files=True)
        self.assertEqual(config['output_directory'], 'test-output')
        self.assertEqual(len(config['files']), 5)
        self.assertTrue(all(file['null'] == 'NULL' for file in config['files']))
        self.assertEqual(window.settings.values()['json_indent'], 4)

        dataset = window.batch.datasets[0]
        self.assertTrue(dataset.model.setData(dataset.model.index(0, 0), 'edited-provider'))
        self.assertEqual(dataset.config()['sample_rows'][0][dataset.columns[0][0]], 'edited-provider')
        dataset.exception_enabled.setChecked(True)
        dataset.preset.setCurrentText('Empty file')
        dataset.apply_exception()
        self.assertEqual(dataset.model.records, [])
        dataset.restore()
        self.assertTrue(dataset.model.records)

        window.history.record(dict(payload={'event_id': 'history-event', 'payment_id': 'payment'},
                                   scenario='Current history', outcome='accepted'))
        window.history.table.selectRow(0)
        app.processEvents()
        self.assertIn('history-event', window.history.preview.toPlainText())
        self.assertEqual(window.history.model.records[0]['outcome'], 'accepted')
        self.assertTrue(window.history.model.records[0]['dispatched_at'])

    def test_history_logs_outcomes_without_drafts_or_demo_controls(self):
        window = self.window
        self.select_case(window.test_cases.cases[0])
        self.assertEqual(window.history.records, [])
        item = dict(payload={'event_id': 'one', 'event_type': 'authorization_requested'},
                    token=window.stack.items[0]['token'], case_id='PL-0001', outcome='failed',
                    transport_error='Service unavailable')
        window.item_updated(item)
        stream = dict(payload={'event_id': 'two'}, stream=True, outcome='accepted')
        window.stream_item_updated(stream)
        item['payload']['event_id'] = 'changed'
        self.assertEqual(len(window.history.records), 2)
        self.assertEqual(window.history.records[0]['payload']['event_id'], 'one')
        self.assertEqual(window.history.model.index(0, 5).data(), 'Failed')
        self.assertEqual(window.history.model.index(0, 6).data(), 'Service unavailable')
        self.assertEqual(window.history.model.index(1, 1).data(), 'Streaming')
        window.history.table.selectRow(0)
        app.processEvents()
        self.assertIn('one', window.history.preview.toPlainText())
        from PySide6.QtWidgets import QLineEdit, QComboBox, QPushButton
        for widget_type in (QLineEdit, QComboBox, QPushButton):
            self.assertEqual(window.history.findChildren(widget_type), [])



class CasePreparationTests(unittest.TestCase):
    def setUp(self):
        sql_patch = patch('Transaction_TestCases.TestCaseClass.create_sql_connection', side_effect=sql_cursor)
        sql_patch.start()
        self.addCleanup(sql_patch.stop)

    def test_terminal_query_is_filtered_and_closes_connection(self):
        from paylens_ui.services import load_terminals
        cursor = Mock()
        connection = cursor.connection
        cursor.fetchall.return_value = [SimpleNamespace(terminal_id='T22', location_name='Branch')]
        with patch('paylens_ui.services.create_sql_connection', return_value=cursor):
            self.assertEqual(load_terminals(22), [('T22', 'Branch')])
        self.assertEqual(cursor.execute.call_args.args[1], 22)
        self.assertIn('WHERE merchant_id = ?', cursor.execute.call_args.args[0])
        cursor.close.assert_called_once()
        connection.close.assert_called_once()
        cursor.execute.side_effect = RuntimeError('Database unavailable')
        with patch('paylens_ui.services.create_sql_connection', return_value=cursor):
            with self.assertRaisesRegex(RuntimeError, 'Database unavailable'):
                load_terminals(22)
        self.assertEqual(connection.close.call_count, 2)

    def test_existing_runner_is_called_with_its_original_signature(self):
        reader = TestCasesFromExcelReader(ROOT / 'Transactions_TestCases.xlsx')
        reader.read_test_cases()
        reader.read_test_steps()
        record = reader.TestCases[0]
        sent = []
        case = TestCaseClass(record, record['Case ID'], reader.TestStepsPerTestCase,
                             merchant={"merchant_id": "mer_001"}, callback_function_sender=sent.append)
        self.assertFalse(hasattr(case, 'prepare_steps'))
        for step in case.TestSteps:
            step.DispatchEvent = 0
        with patch('Transaction_TestCases.TestCaseClass.create_sql_connection', side_effect=sql_cursor):
            case.run_test_case()
        self.assertEqual(len(sent), 4)
        self.assertEqual(len(case.PreviousDispatchPayloads), 4)
        self.assertEqual(case.TestSteps[-1].payload, sent[-1])
        self.assertEqual(len({json.loads(message)['payment_id'] for message in sent}), 1)

    def test_all_workbook_cases_display_original_step_objects(self):
        reader = TestCasesFromExcelReader(ROOT / 'Transactions_TestCases.xlsx')
        reader.read_test_cases()
        reader.read_test_steps()
        for record in reader.TestCases:
            case = TestCaseClass(record, record['Case ID'], reader.TestStepsPerTestCase)
            with self.subTest(case=case.CaseID):
                items = stack_items(case)
                self.assertEqual(len(items), case.TransactionStepsNumber)
                expected = {'payload', 'step', 'action', 'dispatch_seconds', 'token', 'case_run', 'merchant', 'terminal_id'}
                self.assertTrue(all(set(item) == expected for item in items))
                self.assertTrue(all(isinstance(step, TestStepClass) for step in case.TestSteps))
                self.assertEqual([item['step'] for item in items], [int(step.step) for step in case.TestSteps])
                self.assertEqual([item['dispatch_seconds'] for item in items], [float(step.DispatchEvent) for step in case.TestSteps])

    def test_stack_worker_delegates_order_and_waiting_to_original_runner(self):
        reader = TestCasesFromExcelReader(ROOT / 'Transactions_TestCases.xlsx')
        reader.read_test_cases()
        reader.read_test_steps()
        record = reader.TestCases[0]
        case = TestCaseClass(record, record['Case ID'], reader.TestStepsPerTestCase)
        first = stack_items(case)
        second_case = TestCaseClass(record, record['Case ID'], reader.TestStepsPerTestCase)
        second = stack_items(second_case)
        first[0]['payload']['requested_amount_minor'] = -9
        first[1]['dispatch_seconds'] = 0.25
        # Reverse the UI rows: the original class, rather than the worker,
        # sorts its TestSteps before executing them.
        worker = EventHubDispatchWorker(list(reversed(first)) + second,
                                        {first[0]["case_run"]: case, second[0]["case_run"]: second_case}, merchant_id=24)
        messages, results, progress = [], [], []
        worker.finished.connect(results.extend)
        worker.progress.connect(lambda sent, total: progress.append((sent, total)))
        original = TestCaseClass.run_test_case
        with patch('Transaction_TestCases.TestCaseClass.create_sql_connection', side_effect=sql_cursor), \
             patch('paylens_ui.services.create_sql_connection', side_effect=sql_cursor), \
             patch('paylens_ui.services.select_merchant', return_value=SimpleNamespace(merchant_id=24)), \
             patch('paylens_ui.services.create_event_hub_producer') as create, \
             patch('paylens_ui.services.send_event_hubs_message', side_effect=lambda message, **kwargs: messages.append(json.loads(message))), \
             patch.object(TestCaseClass, 'run_test_case', autospec=True, side_effect=original) as run, \
             patch('Transaction_TestCases.TestCaseClass.time.sleep') as wait:
            worker.run()
        self.assertEqual(run.call_count, 2)
        self.assertEqual([call.args[0] for call in wait.call_args_list], [0.25, 3.1, 63.1, 3.0, 3.1, 63.1])
        self.assertEqual(len(messages), 8)
        self.assertEqual(messages[0]['requested_amount_minor'], -9)
        self.assertTrue(all(message['merchant_id'] == 24 for message in messages))
        self.assertEqual(len({message['payment_id'] for message in messages[:4]}), 1)
        self.assertNotEqual(messages[0]['payment_id'], messages[4]['payment_id'])
        self.assertEqual([item['step'] for item in results], [1, 2, 3, 4, 1, 2, 3, 4])
        self.assertEqual(progress[-1], (8, 8))
        create.assert_called_once()
        create.return_value.close.assert_called_once()

    def test_clock_only_run_does_not_create_event_hubs_client(self):
        record = {'Case ID': 'check-only', 'Transaction journey': 'Observation', 'Why required': 'Observation',
                  'Expected result and reporting purpose': 'No publish', 'Steps': 1}
        rows = [{'Case ID': 'check-only', 'Step': 1, 'Dispatch T+ seconds': 0,
                 'Logical event T+ seconds': 0, 'Event / action': 'CLOCK', 'Source': 'test clock',
                 'Status / check': 'check', 'Payload JSON': None}]
        case = TestCaseClass(record, 'check-only', rows)
        items = stack_items(case)
        worker = EventHubDispatchWorker(items, {items[0]['case_run']: case})
        results, progress = [], []
        worker.finished.connect(results.extend)
        worker.progress.connect(lambda sent, total: progress.append((sent, total)))
        with patch('paylens_ui.services.create_sql_connection', side_effect=sql_cursor), \
             patch('paylens_ui.services.select_merchant', return_value=SimpleNamespace(merchant_id=21)), \
             patch('paylens_ui.services.create_event_hub_producer') as create, \
             patch('paylens_ui.services.send_event_hubs_message') as send:
            worker.run()
        create.assert_not_called()
        send.assert_not_called()
        self.assertEqual(results[0]['outcome'], 'checkpoint')
        self.assertEqual(progress, [(0, 0)])



if __name__ == "__main__":
    unittest.main()
