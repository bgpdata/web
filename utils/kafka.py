from confluent_kafka import Producer, Consumer
from jmxquery import JMXConnection, JMXQuery
from flask import current_app as app
from config import Config

jmx = JMXConnection(
    f"service:jmx:rmi:///jndi/rmi://{Config.KAFKA_JMX_FQDN}/jmxrmi"
)

producer = Producer({
    'bootstrap.servers': Config.KAFKA_FQDN,
})

consumer = Consumer({
    'bootstrap.servers': Config.KAFKA_FQDN,
    'group.id': 'web-consumer',
    'partition.assignment.strategy': 'roundrobin',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True,
    'security.protocol': 'PLAINTEXT',
    'fetch.max.bytes': 50 * 1024 * 1024, # 50 MB
    'session.timeout.ms': 30000,  # For stable group membership
})

def get_kafka_ingest_rate():
    try:
        app.logger.info("Fetching Kafka ingest rate")
        queries = [
            JMXQuery("kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec",
                     attribute="OneMinuteRate")
        ]
        results = jmx.query(queries)
        rate_bytes = results[0].value
        return round(rate_bytes * 8 / 1000, 2) # kbit/s
    except Exception as e:
        app.logger.error(f"JMX query error: {e}")
        return 0