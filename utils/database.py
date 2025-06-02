"""
BGPDATA - A BGP Data Aggregation Service.
© 2024 BGPDATA. All rights reserved.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from config import Config
from datetime import datetime
import threading
import asyncio
import pytz
import time

# Connect to PostgreSQL
PostgreSQL = sessionmaker(
    create_async_engine(
        f"postgresql+asyncpg://{Config.POSTGRESQL_USER}:{Config.POSTGRESQL_PASSWORD}@{Config.POSTGRESQL_HOST}/{Config.POSTGRESQL_DB}",
        echo=False
    ),
    expire_on_commit=False,
    class_=AsyncSession
)

class HeartbeatThread:
    def __init__(self, table, record_id):
        """
        Initialize a heartbeat thread for PostgreSQL.
        
        Args:
            table: SQLAlchemy table model class
            record_id: ID of the record to update
        """
        self.table = table
        self.record_id = record_id
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._heartbeat_loop)
        self.thread.daemon = True  # Thread will be killed when main thread exits
        self.loop = None
        
    def start(self):
        """Start the heartbeat thread."""
        self.thread.start()
        
    def stop(self):
        """Stop the heartbeat thread."""
        self.stop_event.set()
        self.thread.join()
        
    def _heartbeat_loop(self):
        """Main heartbeat loop that updates the record's heartbeat timestamp."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        while not self.stop_event.is_set():
            try:
                self.loop.run_until_complete(self._update_heartbeat())
            except Exception:
                # Ignore any errors
                pass

            # Update every minute
            time.sleep(60)
            
    async def _update_heartbeat(self):
        """Update the heartbeat timestamp in the database."""
        async with PostgreSQL() as session:
            stmt = (
                update(self.table)
                .where(self.table.id == self.record_id)
                .values(heartbeat_at=datetime.now(pytz.utc))
            )
            await session.execute(stmt)
            await session.commit()
