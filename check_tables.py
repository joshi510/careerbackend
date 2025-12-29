"""
Script to check if all required tables exist and create them if missing
Run this if tables are not being created automatically
"""
from database import engine, Base, SessionLocal
from models import (
    User, Student, Counsellor, Question, TestAttempt,
    Answer, Score, InterpretedResult, Career, Section, SectionProgress
)
from sqlalchemy import inspect, text

def check_and_create_tables():
    """Check if tables exist and create missing ones"""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("Existing tables:", existing_tables)
    
    # Create all tables
    print("\nCreating all tables...")
    Base.metadata.create_all(bind=engine)
    
    # Verify students table
    inspector = inspect(engine)
    updated_tables = inspector.get_table_names()
    print("\nUpdated tables:", updated_tables)
    
    if 'students' in updated_tables:
        print("✅ students table exists")
        # Check columns
        columns = [col['name'] for col in inspector.get_columns('students')]
        print(f"   Columns: {columns}")
        
        # Check if mobile_number and education columns exist
        if 'mobile_number' in columns:
            print("✅ mobile_number column exists")
        else:
            print("❌ mobile_number column missing - adding...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE students ADD COLUMN mobile_number VARCHAR(15) NULL"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_students_mobile_number ON students(mobile_number)"))
                conn.commit()
            print("✅ Added mobile_number column")
        
        if 'education' in columns:
            print("✅ education column exists")
        else:
            print("❌ education column missing - adding...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE students ADD COLUMN education VARCHAR(100) NULL"))
                conn.commit()
            print("✅ Added education column")
    else:
        print("❌ students table does not exist")
    
    # Check users table
    if 'users' in updated_tables:
        print("✅ users table exists")
    else:
        print("❌ users table does not exist")

if __name__ == "__main__":
    check_and_create_tables()
    print("\n✅ Table check complete!")

