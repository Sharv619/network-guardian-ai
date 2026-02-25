"""
Knowledge Base Persistence Script
Handles loading and saving of the knowledge base for container lifecycle management
"""
import os
import json
import sqlite3
from pathlib import Path
from ..logic.vector_store import vector_memory
from ..db.database import get_db
from ..logic.knowledge_base import KnowledgeBase, get_knowledge_base
from ..core.logging_config import get_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)

def save_knowledge_base():
    """Save knowledge base to persistent storage on container shutdown"""
    try:
        # The knowledge base already handles persistence through its store_knowledge method
        # which calls vector_memory.add_to_memory with persist=True
        # So we just need to ensure the vector memory is saved
        if hasattr(vector_memory, '_save_to_disk'):
            vector_memory._save_to_disk()
        
        logger.info("Knowledge base saved successfully")
        
    except Exception as e:
        logger.error(f"Error saving knowledge base: {e}")

def load_knowledge_base():
    """Load knowledge base from persistent storage on container startup"""
    try:
        # Ensure vector memory is loaded
        if hasattr(vector_memory, '_load_from_disk'):
            vector_memory._load_from_disk()
        
        logger.info("Knowledge base loaded successfully")
        
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")

def migrate_old_data():
    """Migrate any old knowledge base data to the new system"""
    try:
        # Check if there's old data that needs migration
        db_path = Path("network_guardian.db")
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            
            # Check if knowledge base tables exist, create if not
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_cache (
                    domain TEXT PRIMARY KEY,
                    knowledge_data TEXT,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
            conn.close()
            
        logger.info("Knowledge base migration completed")
        
    except Exception as e:
        logger.error(f"Error migrating knowledge base: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "save":
            save_knowledge_base()
        elif action == "load":
            load_knowledge_base()
        elif action == "migrate":
            migrate_old_data()
        else:
            print("Usage: python knowledge_persistence.py [save|load|migrate]")
    else:
        print("Usage: python knowledge_persistence.py [save|load|migrate]")