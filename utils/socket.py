from flask import current_app as app
from flask_sock import Sock
import gevent

sock = Sock()

class WebSocketBroadcaster:
    def __init__(self, fetch_func, interval=2):
        self.fetch_func = fetch_func
        self.interval = interval
        self.subscribers = set()
        self._loop_task = None

    def register(self, ws):
        self.subscribers.add(ws)

        # Start the broadcast loop greenlet if it's not running
        if self._loop_task is None or self._loop_task.dead:
            # Pass the current app context to the spawned greenlet
            self._loop_task = gevent.spawn(self._loop, app._get_current_object())
            # Give the loop a chance to start
            gevent.sleep(0.1)

        try:
            # This loop just waits for the client to disconnect.
            while True:
                try:
                    # Try to receive with a timeout
                    ws.receive(timeout=0.1)
                except Exception:
                    # Connection is closed
                    break
        finally:
            self.subscribers.discard(ws)

    def _loop(self, app):
        with app.app_context():
            while len(self.subscribers) > 0:
                data = self.fetch_func() 

                for ws in list(self.subscribers):
                    try:
                        ws.send(str(data))
                    except Exception:
                        self.subscribers.discard(ws)
                
            self._loop_task = None