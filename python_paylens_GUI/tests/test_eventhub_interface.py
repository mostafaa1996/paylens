"""Client ownership and concurrent sending checks; no network calls."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path
import sys
from threading import Barrier, get_ident
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import load_settings
from utils.EventHubs_interface import create_event_hub_producer, send_event_hubs_message


class EventHubInterfaceTests(unittest.TestCase):
    def test_two_threads_reuse_independent_clients(self):
        clients = []
        barrier = Barrier(2)

        class Client:
            def __init__(self):
                self.owner = get_ident()
                self.closed = False
                self.messages = []
                self.partition_keys = []

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

            def close(self):
                assert self.owner == get_ident()
                self.closed = True

            def create_batch(self, *, partition_key):
                assert not self.closed
                assert self.owner == get_ident()
                self.partition_keys.append(partition_key)
                return SimpleNamespace(add=self.messages.append)

            def send_batch(self, batch):
                assert not self.closed
                barrier.wait(timeout=2)

        def create(*, conn_str, eventhub_name):
            self.assertEqual(conn_str, "fake-connection")
            self.assertEqual(eventhub_name, "auth_req")
            client = Client()
            clients.append(client)
            return client

        message = json.dumps({"event_id": "event", "payment_id": "payment", "nested": {"null": None}})

        def send_sequence():
            with create_event_hub_producer() as client:
                send_event_hubs_message(message, producer=client)
                self.assertFalse(client.closed)
                send_event_hubs_message(message, producer=client)

        with patch("utils.EventHubs_interface.load_settings", return_value=SimpleNamespace(eventhub_connection_string="fake-connection")), \
             patch("azure.eventhub.EventHubProducerClient.from_connection_string", side_effect=create), \
             patch("utils.EventHubs_interface.EventData", side_effect=lambda value: value):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(send_sequence) for _ in range(2)]
                for future in futures:
                    future.result(timeout=4)
        self.assertEqual(len(clients), 2)
        self.assertNotEqual(clients[0].owner, clients[1].owner)
        self.assertTrue(all(client.closed for client in clients))
        self.assertTrue(all(client.messages == [message, message] for client in clients))
        self.assertTrue(all(client.partition_keys == ["payment", "payment"] for client in clients))

    def test_standalone_calls_close_their_temporary_clients(self):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        with patch("utils.EventHubs_interface.create_event_hub_producer", return_value=client) as create:
            send_event_hubs_message('{"payment_id":"payment"}')
        create.assert_called_once()
        client.send_batch.assert_called_once()
        client.__exit__.assert_called_once()

    def test_borrowed_client_is_not_closed_when_send_fails(self):
        client = Mock()
        client.send_batch.side_effect = RuntimeError("Event Hubs unavailable")
        with self.assertRaisesRegex(RuntimeError, "Event Hubs unavailable"):
            send_event_hubs_message('{"payment_id":"payment"}', producer=client)
        client.close.assert_not_called()

    def test_import_does_not_load_settings_or_create_client(self):
        import utils.EventHubs_interface as module
        with patch("config.load_settings") as settings, \
             patch("azure.eventhub.EventHubProducerClient.from_connection_string") as create:
            importlib.reload(module)
            settings.assert_not_called()
            create.assert_not_called()
        # Restore real references after reload under mocks.
        importlib.reload(module)

    def test_invalid_message_does_not_create_client(self):
        with patch("utils.EventHubs_interface.create_event_hub_producer") as create:
            with self.assertRaisesRegex(ValueError, "JSON object"):
                send_event_hubs_message('[]')
            create.assert_not_called()

    def test_configuration_requires_only_event_hubs(self):
        with patch.dict("os.environ", {"EVENTHUB_CONNECTION_STRING": "fake-connection"}, clear=True), patch("config.load_dotenv"):
            self.assertEqual(load_settings().eventhub_connection_string, "fake-connection")

    def test_missing_connection_reports_its_environment_variable(self):
        with patch.dict("os.environ", {}, clear=True), patch("config.load_dotenv"):
            with self.assertRaisesRegex(ValueError, "EVENTHUB_CONNECTION_STRING"):
                load_settings()


if __name__ == "__main__":
    unittest.main()
