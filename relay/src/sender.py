"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from config import RelayConfig as Config
from libs.bmp import BMPv3
import queue as queueio
import select
import socket
import time

def sender_task(queue, db, logger, events, memory):
    """
    Task to transmit messages from the queue to the OpenBMP TCP socket.
    """

    try:
        started = False # If we have sent at least one message
        backpressure_threshold = 1.0  # Threshold in seconds to detect backpressure
        send_delay = 0.0  # Initial delay between sends

        # Create a connection to the collector
        logger.info(f"Connecting to {Config.OPENBMP_CONNECT}")
        with socket.create_connection((Config.OPENBMP_CONNECT.split(':')[0], int(Config.OPENBMP_CONNECT.split(':')[1])), timeout=300) as sock:
            while True:
                try:
                    # Ensure the connection is alive
                    ready_to_read, _, _ = select.select([sock], [], [], 0)
                    if ready_to_read and not sock.recv(1, socket.MSG_PEEK):
                        raise ConnectionError("TCP connection closed by the peer")

                    # Check for shutdown event
                    if events['shutdown'].is_set():
                        # Terminate the BMP connection
                        sock.sendall(BMPv3.term_message(
                            reason_code=1
                        ))
                        break

                    # Get the message from the queue
                    message, offset, topic, partition, update = queue.get()

                    # Start timing the send operation
                    start_time = time.time()

                    # Send the message
                    sock.sendall(message)
                    memory['bytes_sent'] += len(message)
                    
                    # Measure the time taken for sending the message
                    send_time = time.time() - start_time
                    if send_time > backpressure_threshold:
                        logger.warning(f"Detected backpressure: sending took {send_time:.2f}s")
                        send_delay = min(send_delay + 0.1, 5.0) # Increase delay up to 5 seconds
                    else:
                        send_delay = max(send_delay - 0.05, 0.0) # Gradually reduce delay if no backpressure

                    # Apply the delay before the next send if needed
                    if send_delay > 0:
                        time.sleep(send_delay)

                    if not started and update:
                        started = True
                        # Set database as started
                        db.set(b'started', b'\x01')

                    if partition != -1 and topic is not None:
                        key = f'offset_{topic}_{partition}'.encode('utf-8')
                        db.set(key, offset.to_bytes(16, byteorder='big'))

                    # Message sent.
                    queue.task_done()

                except queueio.Empty:
                    # Sleep a bit if the queue is empty.
                    time.sleep(0.1)
                except ConnectionError as e:
                    # Connection lost, raise the error.
                    logger.error("TCP connection lost", exc_info=True)
                    raise e
                except Exception as e:
                    # Some other error occurred
                    logger.error("Error sending message over TCP", exc_info=True)
                    raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        events['shutdown'].set()
        raise e