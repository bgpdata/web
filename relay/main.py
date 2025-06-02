"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from relay.src.kafka import kafka_task
from relay.src.rib import rib_task
from relay.src.sender import sender_task
from relay.src.logging import logging_task
from concurrent.futures import ThreadPoolExecutor
from libs.bmp import BMPv3
import queue as queueio
import rocksdbpy
import threading
import asyncio
import logging
import signal
import os

# Logger
logger = logging.getLogger(__name__)
log_level = os.getenv('RELAY_LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Environment variables
OPENBMP_CONNECT = os.getenv('RELAY_OPENBMP_CONNECT')
KAFKA_CONNECT = os.getenv('RELAY_KAFKA_CONNECT')
HOST = os.getenv('RELAY_HOST')

# Signal handler
def handle_shutdown(signum, frame, event):
    """
    Signal handler for shutdown.

    Args:
        signum (int): The signal number.
        frame (frame): The signal frame.
        shutdown_event (asyncio.Event): The shutdown event.
    """
    logger.info(f"Signal {signum}. Triggering shutdown...")
    event.set()

# Main Coroutine
async def main():
    memory = {
        'task': None,
        'time_lag': {},
        'bytes_sent': 0,
        'bytes_received': 0,
        'rows_processed': 0,
    }

    events = {
        'injection': threading.Event(),
        'shutdown': threading.Event(),
    }

    # Queue
    queue = queueio.Queue(maxsize=10000000)

    # Executor
    executor = ThreadPoolExecutor(max_workers=4)

    # Database
    db = rocksdbpy.open_default("/var/lib/rocksdb")

    try:
        logger.info("Starting up...")

        # Register SIGTERM handler
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, handle_shutdown, signal.SIGTERM, None, events['shutdown'])
        loop.add_signal_handler(signal.SIGINT, handle_shutdown, signal.SIGINT, None, events['shutdown'])  # Handle Ctrl+C

        # Validate database state
        if db.get(b'started') == b'\x01':
            if not db.get(b'ready') == b'\x01':
                # Database is in an inconsistent state
                raise RuntimeError("Corrupted database")

        # Initialize the BMP connection
        message = BMPv3.init_message(
            router_name=f'{HOST}.ripe.net' if HOST.startswith('rrc') else HOST,
            router_descr=f'{HOST}.ripe.net' if HOST.startswith('rrc') else f'{HOST}.routeviews.org'
        )
        queue.put((message, 0, None, -1, False))

        # Start rib task
        loop.run_in_executor(executor, rib_task, HOST, queue, db, logger, events, memory)

        # Start kafka task
        loop.run_in_executor(executor, kafka_task, HOST, KAFKA_CONNECT, queue, db, logger, events, memory)

        # Start sender task
        loop.run_in_executor(executor, sender_task, OPENBMP_CONNECT, queue, db, logger, events, memory)

        # Start logging task
        loop.run_in_executor(executor, logging_task, HOST, queue, logger, events, memory)

        # Wait for the shutdown event
        events['shutdown'].wait()
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        logger.info("Shutting down...")

        # Shutdown the executor
        executor.shutdown(wait=False, cancel_futures=True)

        logger.info("Shutdown complete.")

        # Terminate
        os._exit(1)

if __name__ == "__main__":
    main()