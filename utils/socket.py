from bgpdata.api.parsed.message.Subscription import Subscription
from confluent_kafka import KafkaError, KafkaException
from utils.kafka import consumer, producer
from flask import current_app as app
from collections import defaultdict
from flask_sock import Sock
import gevent
from gevent.lock import RLock
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
            self._stop_event = gevent.event.Event()
            self._broadcaster_greenlet = None
            self._lock = RLock()
            self.initialized = True

    def init_app(self, app):
        self.app = app

    def start(self):
        with self.app.app_context():
            if Broadcaster._is_running:
                app.logger.warn("Broadcaster is already running.")
                return
            
            if self._broadcaster_greenlet and not self._broadcaster_greenlet.dead:
                app.logger.warn("Broadcaster greenlet is already alive.")
                return
            
            self._stop_event.clear()
            self._broadcaster_greenlet = gevent.spawn(self._run)
            self._broadcaster_greenlet.name = "BroadcasterGreenlet"
            Broadcaster._is_running = True

            # Log the greenlet ID
            app.logger.info(f"Started Broadcaster greenlet [{id(self._broadcaster_greenlet)}]")

    def shutdown(self, wait=True):
        with self.app.app_context():
            if not Broadcaster._is_running:
                return
                
            self._stop_event.set()
            if self._broadcaster_greenlet and not self._broadcaster_greenlet.dead:
                if wait:
                    self._broadcaster_greenlet.join()
                else:
                    self._broadcaster_greenlet.kill()
            Broadcaster._is_running = False

            # Log the shutdown
            app.logger.info("Broadcaster shutdown complete.")

    def _run(self):
        with self.app.app_context():
            while not self._stop_event.is_set():
                try:
                    # Reduce batch size and timeout for more frequent processing
                    msgs = consumer.consume(1000, timeout=0.1)
                    if not msgs:
                        gevent.sleep(0.1)  # Use gevent.sleep instead of time.sleep
                        continue

                    # Process messages in smaller batches
                    for msg in msgs:
                        if msg.error():
                            if msg.error().code() == KafkaError._PARTITION_EOF:
                                gevent.sleep(0.1)
                                continue
                            elif msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                                gevent.sleep(0.5)
                                continue
                            else:
                                app.logger.error(f"Kafka error: {msg.error()}", exc_info=True)
                                raise KafkaException(msg.error())

                        try:
                            # Process the message
                            value = Subscription(msg.value()).to_json()
                            self.broadcast(value.content.resource, value.content.action)
                        except Exception as e:
                            app.logger.error(f"Error processing message: {str(e)}", exc_info=True)
                            continue

                except KafkaException as e:
                    if e.args[0].code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        gevent.sleep(0.5)
                        continue
                    raise

    def register(self, ws, resource):
        with self._lock:
            self.subscriptions[resource].add(ws)
            producer.produce(
                topic=f"bgpdata.parsed.subscription",
                key=resource,
                value=bytes(Subscription(resource=resource, action="subscribe")),
                timestamp=int(time.time() * 1000)
            )

    def unregister(self, ws, resource):
        with self._lock:
            self.subscriptions[resource].discard(ws)
            if not self.subscriptions[resource]:
                del self.subscriptions[resource]

    def broadcast(self, resource, action):
        if resource in self.subscriptions:
            with self._lock:
                # Create a copy of the set to avoid modification during iteration
                websockets = list(self.subscriptions[resource])
            
            for ws in websockets:
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