"""
Test script to verify student registration creates both user and student records
Run this to test the registration flow
"""
from database import SessionLocal, engine
from models import User, Student, UserRole
from sqlalchemy import inspect

def test_registration():
    """Test that registration creates both user and student"""
    db = SessionLocal()
    
    try:
        # Check tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📊 Available tables: {tables}")
        
        if 'users' not in tables:
            print("❌ users table does not exist!")
            return
        if 'students' not in tables:
            print("❌ students table does not exist!")
            return
        
        # Check current counts
        user_count = db.query(User).filter(User.role == UserRole.STUDENT).count()
        student_count = db.query(Student).count()
        
        print(f"\n📈 Current counts:")
        print(f"   Students (users table): {user_count}")
        print(f"   Students (students table): {student_count}")
        
        # Show all students
        print(f"\n📋 All student records in students table:")
        all_students = db.query(Student).all()
        if all_students:
            for s in all_students:
                user = db.query(User).filter(User.id == s.user_id).first()
                print(f"   - Student id={s.id}, user_id={s.user_id}, mobile={s.mobile_number}, education={s.education}, user_email={user.email if user else 'NOT FOUND'}")
        else:
            print("   (No student records found)")
        
        # Check for orphaned users (users without student profiles)
        print(f"\n🔍 Checking for orphaned student users (users without student profiles):")
        all_student_users = db.query(User).filter(User.role == UserRole.STUDENT).all()
        orphaned = []
        for user in all_student_users:
            student = db.query(Student).filter(Student.user_id == user.id).first()
            if not student:
                orphaned.append(user)
                print(f"   ❌ User id={user.id}, email={user.email} has NO student profile!")
        
        if not orphaned:
            print("   ✅ All student users have corresponding student profiles")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_registration()

