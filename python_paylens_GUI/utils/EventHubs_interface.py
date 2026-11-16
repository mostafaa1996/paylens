"""Event Hubs clients are owned by individual workers, never shared globally."""
import json
from azure.eventhub import EventHubProducerClient, EventData
from config import load_settings


def create_event_hub_producer():
    """Create a client in its owning thread; the caller must close it."""
    settings = load_settings()
    return EventHubProducerClient.from_connection_string(
        conn_str=settings.eventhub_connection_string,
        eventhub_name="auth_req",
    )


def send_event_hubs_message(message, *, producer=None):
    """Send JSON with a caller-owned client, or a temporary standalone client.

    Each worker must own a separate producer and close it when finished.
    Supplied producers are reused and are never closed by this function.
    """
    message_dict = json.loads(message)
    if not isinstance(message_dict, dict):
        raise ValueError("The message must be a JSON object")
    if producer is None:
        with create_event_hub_producer() as owned_producer:
            _send_message(message, message_dict, owned_producer)
    else:
        _send_message(message, message_dict, producer)


def _send_message(message, message_dict, producer):
    event_data_batch = producer.create_batch(
        partition_key=message_dict.get("payment_id")
    )
    event_data_batch.add(EventData(message))
    producer.send_batch(event_data_batch)
