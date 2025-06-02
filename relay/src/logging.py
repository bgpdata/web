"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
import time

def logging_task(host, queue, logger, events, memory):
    """
    Task to periodically log the current state of the collector.
    """

    try:
        while True:
            timeout = 10

            # Compute kbit/s
            kbps_sent = (memory['bytes_sent'] * 8) / timeout / 1000
            kbps_received = (memory['bytes_received'] * 8) / timeout / 1000

            # Compute time lag
            time_lag_values = memory['time_lag'].values()
            maximum_lag = max(time_lag_values, default=0)  # Default to 0 if empty
            h, remainder = divmod(maximum_lag.total_seconds() if maximum_lag else 0, 3600)
            m, s = divmod(remainder, 60)

            match memory['task']:
                case 'rib':
                    logger.info(f"host={host} task={memory['task']} processing={memory['rows_processed']} rps receive={kbps_received:.2f} kbps send={kbps_sent:.2f} kbps queued={queue.qsize()}")
                case 'kafka':
                    logger.info(f"host={host} task={memory['task']} lag={int(h)}h {int(m)}m {int(s)}s receive={kbps_received:.2f} kbps send={kbps_sent:.2f} kbps queued={queue.qsize()}")
                case _:
                    logger.info(f"host={host} task={memory['task']} receive={kbps_received:.2f} kbps send={kbps_sent:.2f} kbps queued={queue.qsize()}")
                
            # Reset trackers
            memory['bytes_sent'] = 0
            memory['bytes_received'] = 0
            memory['rows_processed'] = 0
            time.sleep(timeout)
    except Exception as e:
        logger.error(e, exc_info=True)
        events['shutdown'].set()
        raise e