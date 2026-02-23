#!/usr/bin/env python3
"""Database initialization script"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database import init_db, SessionLocal, Device, ModelProfile

def main():
    print("Initializing database...")
    init_db()
    print("✓ Database tables created")
    
    # Add sample data
    db = SessionLocal()
    try:
        # Add default device
        if db.query(Device).count() == 0:
            device = Device(
                name="Default Switch",
                ip="192.168.1.1",
                port=22,
                vendor="generic",
                enabled=True
            )
            db.add(device)
            print("✓ Added default device")
        
        # Add default model profile
        if db.query(ModelProfile).count() == 0:
            model = ModelProfile(
                model_name="llama2",
                model_type="local",
                is_local=True,
                priority=1,
                enabled=True
            )
            db.add(model)
            print("✓ Added default model profile")
        
        db.commit()
        print("\n✓ Database initialization complete!")
        print("\nYou can now start the server with: python main.py")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()