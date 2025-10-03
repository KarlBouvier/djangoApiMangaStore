"""
Database connection signals and optimizations
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(connection_created)
def optimize_sqlite_connection(sender, connection, **kwargs):
    """
    Optimize SQLite connection when created
    """
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            
            # Optimize for performance
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=10000;")
            cursor.execute("PRAGMA temp_store=MEMORY;")
            cursor.execute("PRAGMA mmap_size=268435456;")  # 256MB
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON;")
            
            # Optimize the database
            cursor.execute("PRAGMA optimize;")
            
            logger.info("SQLite connection optimized with WAL mode and performance settings")
