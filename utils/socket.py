from bgpdata.api.parsed.message.Subscription import Subscription
from confluent_kafka import KafkaError, KafkaException
from utils.kafka import consumer, producer
from flask import current_app as app
from collections import defaultdict
from flask_sock import Sock
import threading
import time

sock = Sock()

consumer.subscribe(
    ['bgpdata.parsed.notification']
)

class Socket:
    def __init__(self, app):
        self.subscriptions = defaultdict(set)
        self._socket_thread = threading.Thread(target=self._run, daemon=True)
        self._socket_thread.name = "SocketThread"
        self._socket_thread.start()
        self.app = app

    def _run(self):
        with self.app.app_context():
            while True:
                msgs = consumer.consume(100000, timeout=0.1)
                if not msgs:
                    continue
                for msg in msgs:
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # Kafka Broker tells us we are too fast, sleep a bit.
                            time.sleep(0.5)
                            continue
                        else:
                            # Some other error occurred
                            app.logger.error(f"Kafka error: {msg.error()}", exc_info=True)
                            raise KafkaException(msg.error())

                    # Process the message
                    value = Subscription(msg.value()).to_json()
                    self.broadcast(value.content.resource, value.content.action)

    def register(self, ws, resource):
        self.subscriptions[resource].add(ws)
        producer.produce(
            topic=f"bgpdata.parsed.subscription",
            key=resource,
            value=Subscription(resource=resource, action="subscribe"),
            timestamp=int(time.time() * 1000)
        )

    def unregister(self, ws, resource):
        self.subscriptions[resource].discard(ws)
        if not self.subscriptions[resource]:
            del self.subscriptions[resource]

    def broadcast(self, resource, action):
        if resource in self.subscriptions:
            for ws in list(self.subscriptions[resource]):
                try:
                    ws.send(action)
                except Exception:
                    self.unregister(ws, resource)