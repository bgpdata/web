"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from flask import current_app as app
import heapq
import time
import threading
import random

class Job:
    def __init__(self, id, func, interval_seconds, priority):
        self.id = id
        self.func = func
        self.interval_seconds = interval_seconds
        self.priority = priority
        self.next_run_time = time.time()

    def __lt__(self, other):
        # For heap ordering: earlier next_run_time comes first.
        # If next_run_times are equal, lower priority number (higher actual priority) comes first.
        if self.next_run_time == other.next_run_time:
            # Lower priority number means higher priority
            return self.priority < other.priority 
        return self.next_run_time < other.next_run_time

class Scheduler:
    _instance = None
    _is_running = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
        return cls._instance

    def __init__(self, num_threads=1):
        if not hasattr(self, 'initialized'):
            self.app = None
            self.job_queue = [] # Min-heap (priority queue)
            self.executor = ThreadPoolExecutor(max_workers=num_threads)
            self._lock = threading.Lock()
            self._stop_event = threading.Event()
            self._scheduler_thread = None
            self.active_job_ids = set()
            self.initialized = True

    def _job_wrapper(self, job):
        # This runs in the ThreadPoolExecutor
        with self.app.app_context():
            try:
                with self._lock:
                    self.active_job_ids.add(job.id)
                
                # Random delay to prevent thundering herd
                delay = random.uniform(0, 5)
                time.sleep(delay)

                # Track execution time
                start_time = time.time()
                
                app.logger.debug(f"Executing {job.id} (priority: {job.priority})")
                job.func(self.app)
                app.logger.debug(f"Completed {job.id} (duration: {time.time() - start_time:.2f}s)")
            except Exception as e:
                app.logger.error(f"Error in {job.id}: {str(e)}")
            finally:
                with self._lock:
                    self.active_job_ids.remove(job.id)
                    # Reschedule the job based on its completion time
                    job.next_run_time = time.time() + job.interval_seconds
                    heapq.heappush(self.job_queue, job)

    def init_app(self, app):
        self.app = app

    def add_job(self, id, func, priority, days=0, hours=0, minutes=0, seconds=0):
        with self.app.app_context():
            interval = timedelta(
                days=days,
                hours=hours,
                minutes=minutes,
                seconds=seconds
            ).total_seconds()

            if interval <= 0:
                raise ValueError("Job interval must be positive.")

            job = Job(id=id, func=func,
                    interval_seconds=interval, priority=priority)
            
            with self._lock:
                heapq.heappush(self.job_queue, job)

    def _run(self):
        with self.app.app_context():
            while not self._stop_event.is_set():
                now = time.time()
                job_popped = None

                with self._lock:
                    if self.job_queue and self.job_queue[0].next_run_time <= now:
                        job_popped = heapq.heappop(self.job_queue)
                
                if job_popped:
                    should_run_job = False
                    with self._lock: # Lock for checking active_job_ids
                        if job_popped.id not in self.active_job_ids:
                            should_run_job = True
                    
                    if should_run_job:
                        app.logger.debug(f"Submitting {job_popped.id} (priority: {job_popped.priority})")
                        # _job_wrapper will add to active_job_ids and reschedule upon completion
                        self.executor.submit(self._job_wrapper, job_popped)
                    else:
                        # Job is already active. This specific scheduled instance is skipped.
                        # The currently running instance will reschedule itself when it's done.
                        app.logger.debug(f"Skipping {job_popped.id} as an instance is already active.")
                else:
                    # Adaptive sleep: wait until the next job is due or for a short interval
                    sleep_time = 1.0  # Default sleep time if queue is empty
                    with self._lock:
                        if self.job_queue:
                            # Calculate time until next job, but don't sleep too long or too short
                            sleep_time = max(0.1, min(1.0, self.job_queue[0].next_run_time - now))
                    time.sleep(sleep_time)

    def start(self):
        with self.app.app_context():
            if Scheduler._is_running:
                app.logger.warn("Scheduler is already running.")
                return
            
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                app.logger.warn("Scheduler thread is already alive.")
                return
            
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(target=self._run, daemon=True)
            self._scheduler_thread.name = "SchedulerThread"
            self._scheduler_thread.start()
            Scheduler._is_running = True

            # Log the thread ID
            app.logger.info(f"Started scheduler thread [{self._scheduler_thread.ident}]")

    def shutdown(self, wait=True):
        with self.app.app_context():
            if not Scheduler._is_running:
                return
                
            self._stop_event.set()
            self.executor.shutdown(wait=wait)
            if self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join()
            Scheduler._is_running = False

            # Log the shutdown
            app.logger.info("Scheduler shutdown complete.")

# Initialize
scheduler = Scheduler(num_threads=1)
