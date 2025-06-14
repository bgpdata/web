from jmxquery import JMXConnection, JMXQuery
from flask import current_app as app

jmx = JMXConnection("service:jmx:rmi:///jndi/rmi://kafka:9999/jmxrmi")

def get_kafka_ingest_rate():
    try:
        app.logger.info("Fetching Kafka ingest rate")
        queries = [JMXQuery("kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec", attribute="OneMinuteRate")]
        results = jmx.query(queries)
        rate_bytes = results[0].value
        return round(rate_bytes * 8 / 1000, 2) # kbit/s
    except Exception as e:
        app.logger.error(f"JMX query error: {e}")
        return 0