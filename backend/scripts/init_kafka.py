"""Create Kafka topics used by the pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from confluent_kafka.admin import AdminClient, NewTopic

from app.config import settings

TOPICS = [settings.kafka_topic_raw_docs, settings.kafka_topic_ocr_complete,
          settings.kafka_topic_entities_raw, settings.kafka_topic_entities_tagged]

if __name__ == "__main__":
    admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    futures = admin.create_topics([NewTopic(t, num_partitions=3, replication_factor=1)
                                   for t in TOPICS])
    for topic, f in futures.items():
        try:
            f.result()
            print(f"Created topic {topic}")
        except Exception as e:
            print(f"Topic {topic}: {e}")
