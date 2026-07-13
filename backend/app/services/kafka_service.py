"""Kafka producer/consumer helpers (confluent-kafka)."""
import json
import logging

from confluent_kafka import Consumer, Producer

from app.config import settings

logger = logging.getLogger(__name__)

_producer: Producer | None = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})
    return _producer


def publish(topic: str, payload: dict):
    p = get_producer()
    p.produce(topic, json.dumps(payload).encode())
    p.flush(timeout=10)
    logger.info("Published to %s: %s", topic, payload.get("file_id", payload))


def make_consumer(topics: list[str], group_id: str) -> Consumer:
    c = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
    })
    c.subscribe(topics)
    return c


def consume_loop(consumer: Consumer, handler):
    """Blocking poll loop. handler(payload_dict) is called per message."""
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error("Kafka error: %s", msg.error())
            continue
        try:
            handler(json.loads(msg.value().decode()))
        except Exception:
            logger.exception("Handler failed for message on %s", msg.topic())
