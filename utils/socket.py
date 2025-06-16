from bgpdata.api.parsed.message.Subscription import Subscription
from confluent_kafka import KafkaError, KafkaException
from concurrent.futures import ThreadPoolExecutor
from utils.kafka import consumer, producer
from flask import current_app as app
from collections import defaultdict
from flask_sock import Sock
import threading
import time
import json

sock = Sock()

consumer.subscribe(
    ['bgpdata.parsed.notification']
)

class Broadcaster:
    _instance = None
    _is_running = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Broadcaster, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.subscriptions = defaultdict(set)
            self.executor = ThreadPoolExecutor(max_workers=1)
            self._stop_event = threading.Event()
            self._broadcaster_thread = None
            self.initialized = True

    def init_app(self, app):
        self.app = app

    def start(self):
        with self.app.app_context():
            if Broadcaster._is_running:
                app.logger.warn("Broadcaster is already running.")
                return
            
            if self._broadcaster_thread and self._broadcaster_thread.is_alive():
                app.logger.warn("Broadcaster thread is already alive.")
                return
            
            self._stop_event.clear()
            self._broadcaster_thread = threading.Thread(target=self._run, daemon=True)
            self._broadcaster_thread.name = "BroadcasterThread"
            self._broadcaster_thread.start()
            Broadcaster._is_running = True

            # Log the thread ID
            app.logger.info(f"Started Broadcaster thread [{self._broadcaster_thread.ident}]")

    def shutdown(self, wait=True):
        with self.app.app_context():
            if not Broadcaster._is_running:
                return
                
            self._stop_event.set()
            self.executor.shutdown(wait=wait)
            if self._broadcaster_thread and self._broadcaster_thread.is_alive():
                self._broadcaster_thread.join()
            Broadcaster._is_running = False

            # Log the shutdown
            app.logger.info("Broadcaster shutdown complete.")

    def _run(self):
        with self.app.app_context():
            while not self._stop_event.is_set():
                try:
                    msgs = consumer.consume(100000, timeout=0.1)
                    if not msgs:
                        continue
                    for msg in msgs:
                        if msg.error():
                            if msg.error().code() == KafkaError._PARTITION_EOF:
                                time.sleep(0.5)
                                continue
                            elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                                time.sleep(1)
                                continue
                            else:
                                app.logger.error(f"Kafka error: {msg.error()}", exc_info=True)
                                raise KafkaException(msg.error())

                        # Process the message
                        value = Subscription(msg.value()).to_json()
                        self.broadcast(value.content.resource, value.content.action)
                except KafkaException as e:
                    if e.args[0].code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        time.sleep(1)
                        continue
                    raise

    def register(self, ws, resource):
        self.subscriptions[resource].add(ws)
        producer.produce(
            topic=f"bgpdata.parsed.subscription",
            key=resource,
            value=bytes(Subscription(resource=resource, action="subscribe")),
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
                    # Ensure the message is properly formatted as JSON
                    if isinstance(action, str):
                        try:
                            # If it's already a JSON string, validate it
                            json.loads(action)
                            message = action
                        except json.JSONDecodeError:
                            # If it's not JSON, wrap it in a JSON object
                            message = json.dumps({"action": action})
                    else:
                        # If it's not a string, convert it to JSON
                        message = json.dumps({"action": action})
                    
                    ws.send(message)
                except Exception as e:
                    app.logger.error(f"Error broadcasting to WebSocket: {str(e)}", exc_info=True)
                    self.unregister(ws, resource)

broadcaster = Broadcaster()