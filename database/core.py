from peewee import SqliteDatabase, Model, PostgresqlDatabase, MySQLDatabase
from playhouse.db_url import connect
import os
from config import DATABASE_URL

# Determine database type from URL and create appropriate instance
if DATABASE_URL.startswith('postgresql://'):
    db = PostgresqlDatabase(None)  # Will be initialized from URL
elif DATABASE_URL.startswith('mysql://'):
    db = MySQLDatabase(None)
else:
    # Default to SQLite
    db = SqliteDatabase(None)

# Initialize database from URL
db_connection = connect(DATABASE_URL)

class BaseModel(Model):
    class Meta:
        database = db_connection

def init_database():
    """Initialize database connection and create tables"""
    
    
    # Connect to database
    db_connection.connect()
    
    # Create tables (in production, you might use migrations instead)
    from .models import (
        Harness, ConnectorType, ProtectionType, WireType, 
        Connector, Pin, BranchProtection, Node, Wire, 
        HarnessBranch, BranchSegment, BranchPath
    )
    
    tables = [
        Harness, ConnectorType, ProtectionType, WireType,
        Connector, Pin, BranchProtection, Node, Wire,
        HarnessBranch, BranchSegment, BranchPath
    ]
    
    db_connection.create_tables(tables, safe=True)
    print("Database tables created successfully")

def close_database():
    """Close database connection"""
    if not db_connection.is_closed():
        db_connection.close()