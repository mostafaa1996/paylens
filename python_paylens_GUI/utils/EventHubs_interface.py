from azure.eventhub import EventHubProducerClient, EventData
import json
from config import load_settings

settings = load_settings()

producer = EventHubProducerClient.from_connection_string(
        conn_str=settings.eventhub_connection_string, 
        eventhub_name="auth_req"
        )
def send_event_hubs_message(message):
    message_dict = json.loads(message)
    with producer:
        event_data_batch = producer.create_batch(
            partition_key= message_dict.get("payment_id")
        )
        event_data_batch.add(EventData(message))
        producer.send_batch(event_data_batch)