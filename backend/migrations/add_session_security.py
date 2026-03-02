"""
Migration: Add security fields to ai_chat_session
- Add user_id foreign key for ownership tracking
- Add expires_at for session expiration
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "..", "aimiguard.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ai_chat_session)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "user_id" not in columns:
            print("Adding user_id column...")
            cursor.execute("""
                ALTER TABLE ai_chat_session 
                ADD COLUMN user_id INTEGER REFERENCES user(id)
            """)
            # Set default user_id to 1 (admin) for existing sessions
            cursor.execute("UPDATE ai_chat_session SET user_id = 1 WHERE user_id IS NULL")
            print("✓ user_id column added")
        
        if "expires_at" not in columns:
            print("Adding expires_at column...")
            cursor.execute("""
                ALTER TABLE ai_chat_session 
                ADD COLUMN expires_at DATETIME
            """)
            print("✓ expires_at column added")
        
        # Create index on user_id for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_chat_session_user_id 
            ON ai_chat_session(user_id)
        """)
        print("✓ Index created on user_id")
        
        conn.commit()
        print("\n✅ Migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
