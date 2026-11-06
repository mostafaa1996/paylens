"""Integration signals and Kafka work that stays off the Qt UI thread."""
from threading import Event
from time import monotonic

from PySide6.QtCore import QObject, Signal, Slot
from .domain import snapshot, now, new_id


class IntegrationHooks(QObject):
    request_send_event = Signal(object, object)
    request_send_stack = Signal(object, object)
    request_generate_batch_files = Signal(object)
    request_generate_customers = Signal(object)
    request_generate_merchants = Signal(object)
    request_export = Signal(str, object, object)
    request_save_history = Signal(object, object)
    request_test_connection = Signal(object)
    feedback = Signal(str)

    def __init__(self):
        super().__init__()
        for name in ("request_generate_batch_files", "request_generate_customers", "request_generate_merchants", "request_test_connection"):
            getattr(self, name).connect(lambda config, n=name: self.feedback.emit(f"SIMULATED: {n.removeprefix('request_')} configuration received. No external operation performed."))
        self.request_export.connect(lambda kind, selection, options: self.feedback.emit(f"SIMULATED: {kind} export requested for {len(selection)} item(s). No files written."))
        self.request_save_history.connect(lambda payload, metadata: self.feedback.emit("SIMULATED: history save requested; pending integration. No file saved."))


class KafkaDispatchWorker(QObject):
    """Publish one dispatch run sequentially and report broker delivery results."""

    item_updated = Signal(object)
    progress = Signal(int, int)
    finished = Signal(object)

    def __init__(self, items, options, settings, delivery_timeout=30):
        super().__init__()
        self.items = snapshot(items)
        self.options = snapshot(options)
        self.settings = settings
        self.delivery_timeout = delivery_timeout
        self._cancel_requested = Event()

    def cancel(self):
        # The current Kafka publish is allowed to finish; only unsent items cancel.
        self._cancel_requested.set()

    def _update(self, item, state, outcome, run_id, error=None):
        item.update(state=state, outcome=outcome, run_id=run_id,
                    attempt_id=new_id("kafka_attempt"), dispatched_at=now())
        if error:
            item["transport_error"] = error
        else:
            item.pop("transport_error", None)
        self.item_updated.emit(snapshot(item))

    @Slot()
    def run(self):
        from kafka_IO import create_producer, produce_kafka_message

        run_id = new_id("kafka_run")
        queue = snapshot(self.items)
        if self.options.get("out_of_order"):
            queue.reverse()
        if self.options.get("duplicate_dispatch"):
            queue = [snapshot(item) for item in queue for _ in range(2)]
        total = len(queue)
        results = []
        completed = 0
        producer = None

        def cancel_remaining(remaining):
            nonlocal completed
            for pending in remaining:
                self._update(pending, "Cancelled before Kafka publish", "cancelled", run_id)
                results.append(snapshot(pending))
                completed += 1
                self.progress.emit(completed, total)

        try:
            producer = create_producer(self.settings)
            for index, item in enumerate(queue):
                if self._cancel_requested.is_set():
                    cancel_remaining(queue[index:])
                    break

                self.item_updated.emit(snapshot({**item, "state": "Publishing to Kafka"}))
                delivery = {}

                def on_delivery(error, message):
                    delivery["done"] = True
                    delivery["error"] = str(error) if error else None
                    if message is not None:
                        delivery["partition"] = message.partition()
                        delivery["offset"] = message.offset()

                try:
                    produce_kafka_message(
                        item["payload"],
                        item["payload"].get("event_id") if isinstance(item["payload"].get("event_id"), str) else None,
                        item["topic_name"], producer, on_delivery,
                    )
                    deadline = monotonic() + self.delivery_timeout
                    while not delivery.get("done") and monotonic() < deadline:
                        producer.poll(0.1)
                    if not delivery.get("done"):
                        error = f"No Kafka delivery confirmation within {self.delivery_timeout} seconds; delivery outcome is unknown."
                    else:
                        error = delivery.get("error")
                except Exception as exc:
                    error = str(exc)

                if error:
                    self._update(item, "Kafka delivery failed", "failed", run_id, error)
                else:
                    item["kafka_partition"] = delivery.get("partition")
                    item["kafka_offset"] = delivery.get("offset")
                    self._update(item, "Kafka broker acknowledged", "accepted", run_id)
                results.append(snapshot(item))
                completed += 1
                self.progress.emit(completed, total)

                if error and self.options.get("stop_on_error"):
                    cancel_remaining(queue[index + 1:])
                    break
                delay = min(max(self.options.get("delay_ms", 0), 0), 60000) / 1000
                if delay and self._cancel_requested.wait(delay):
                    cancel_remaining(queue[index + 1:])
                    break
        except Exception as exc:
            logger_error = f"Kafka dispatch error: {exc}"
            remaining = queue[completed:]
            cancel_remaining([])
            for pending in remaining:
                self._update(pending, "Kafka publish failed", "failed", run_id, logger_error)
                results.append(snapshot(pending))
                completed += 1
                self.progress.emit(completed, total)
        finally:
            if producer is not None:
                try:
                    producer.flush(timeout=5)
                except Exception:
                    pass
            self.finished.emit(snapshot(results))
