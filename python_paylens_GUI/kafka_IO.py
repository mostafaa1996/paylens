from confluent_kafka import Producer, Consumer, KafkaError
from config import Settings, load_settings
import logging
import json

logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
def create_producer(settings: Settings) -> Producer:
    config = {
        "bootstrap.servers": settings.bootstrap_servers,
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": settings.api_key,
        "sasl.password": settings.api_secret,
        "client.id": "paylens-producer",
        "acks": "all",
        "retries": 5,
        "retry.backoff.ms": 500,
        "message.timeout.ms": 30000,
        "enable.idempotence": True,
    }
    return Producer(config)

def create_consumer(settings: Settings) -> Consumer:
    """Build a Kafka consumer configured for Confluent Cloud."""
    config = {
        "bootstrap.servers": settings.bootstrap_servers,
        "security.protocol": "SASL_SSL",
        "sasl.mechanisms": "PLAIN",
        "sasl.username": settings.api_key,
        "sasl.password": settings.api_secret,
        "group.id": "paylens-consumer-group",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    return Consumer(config)


def produce_kafka_message(payload, event_id, topic_name, producer: Producer, on_delivery=None) -> None:
    """Queue one message on a caller-owned producer; poll/flush and errors belong to the caller."""
    logger.info("Queueing Kafka message for topic=%s", topic_name)
    producer.produce(
        topic=topic_name,
        key=event_id,
        value=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        on_delivery=on_delivery,
    )
        
def consume_kafka_messages(topic_name, settings: Settings | None = None) -> None:
    settings = settings or load_settings()
    consumer = create_consumer(settings)
    try:
        consumer.subscribe([topic_name])
        logger.info("Listening for messages on topic=%s", topic_name)
        message = consumer.poll(timeout=1.0)
        if message.error():
            logger.error("Consumer error: %s", message.error())

        payload = json.loads(message.value().decode("utf-8"))
        logger.info("Received message: %s", json.dumps(payload, indent=2, sort_keys=True))
           
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down consumer.")
    finally:
        consumer.close()    
        
        
