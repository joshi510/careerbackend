from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database import engine, Base, SessionLocal
from routes import auth, test_access, test, student_result, counsellor_notes, admin_analytics
import os
from backend.models import (
    User, Student, Counsellor, Question, TestAttempt,
    Answer, Score, InterpretedResult, Career, UserRole, Section,
    SectionProgress
)
# Import all models to ensure tables are created on startup
from models.student import Student
from models.section import Section
from models.section_progress import SectionProgress
from models.counsellor_note import CounsellorNote
from models.question import QuestionType

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

# CORS configuration - allow frontend URL from environment or default to all origins
frontend_url = os.getenv("FRONTEND_URL", "*")
allowed_origins = [frontend_url] if frontend_url != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # 1️⃣ Create tables
    print("🔵 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")
    
    # Verify students table exists
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📊 Existing tables: {tables}")
    if 'students' in tables:
        print("✅ students table exists")
        columns = [col['name'] for col in inspector.get_columns('students')]
        print(f"   Columns: {columns}")
    else:
        print("❌ WARNING: students table not found!")
    
    # Verify and fix students table structure
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    
    # Check students table
    if 'students' in inspector.get_table_names():
        student_columns = [col['name'] for col in inspector.get_columns('students')]
        print(f"✅ students table exists with columns: {student_columns}")
        
        # Add mobile_number column if missing
        if 'mobile_number' not in student_columns:
            print("🔵 Adding mobile_number column to students table...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE students ADD COLUMN mobile_number VARCHAR(15) NULL"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_students_mobile_number ON students(mobile_number)"))
                    conn.commit()
                print("✅ Added mobile_number column")
            except Exception as e:
                print(f"⚠️ Could not add mobile_number column: {e}")
        
        # Add education column if missing
        if 'education' not in student_columns:
            print("🔵 Adding education column to students table...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE students ADD COLUMN education VARCHAR(100) NULL"))
                    conn.commit()
                print("✅ Added education column")
            except Exception as e:
                print(f"⚠️ Could not add education column: {e}")
    else:
        print("❌ WARNING: students table does not exist! It should be created by Base.metadata.create_all()")
    
    # Add missing correct_answer column if it doesn't exist
    if 'questions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('questions')]
        if 'correct_answer' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE questions ADD COLUMN correct_answer VARCHAR(10) NULL"))
                conn.commit()
            print("✅ Added correct_answer column to questions table")
        
        # Add missing section_id column if it doesn't exist
        if 'section_id' not in columns:
            print("🔵 Adding section_id column to questions table...")
            try:
                with engine.connect() as conn:
                    # Add the column first
                    conn.execute(text("ALTER TABLE questions ADD COLUMN section_id INTEGER NULL"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_questions_section_id ON questions(section_id)"))
                    
                    # Then add foreign key constraint if sections table exists
                    if 'sections' in inspector.get_table_names():
                        try:
                            conn.execute(text("ALTER TABLE questions ADD CONSTRAINT fk_questions_section_id FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE SET NULL"))
                        except Exception as fk_error:
                            # Foreign key might already exist or there might be data issues
                            error_msg = str(fk_error).lower()
                            if 'duplicate' in error_msg or 'already exists' in error_msg:
                                print("ℹ️ Foreign key constraint already exists")
                            else:
                                print(f"⚠️ Could not add foreign key constraint: {fk_error}")
                    
                    conn.commit()
                    print("✅ Added section_id column to questions table")
            except Exception as e:
                error_msg = str(e).lower()
                if 'duplicate' in error_msg or 'already exists' in error_msg:
                    print("ℹ️ section_id column may already exist")
                else:
                    print(f"⚠️ Could not add section_id column: {e}")
    
    # 2️⃣ Seed admin user and sample questions
    db = SessionLocal()
    try:
        # Seed admin user
        admin_exists = db.query(User).filter(
            User.role == UserRole.ADMIN
        ).first()

        if not admin_exists:
            admin_user = User(
                email="admin@test.com",
                password_hash="admin123",   # 🔥 TEMP FIX
                full_name="Admin User",
                role=UserRole.ADMIN
            )

            db.add(admin_user)
            db.commit()
            print("✅ Admin user created (TEMP password)")
        else:
            print("ℹ️ Admin already exists")

        # Seed sections if table is empty - EXACTLY 5 sections in mandatory order
        section_count = db.query(Section).count()
        if section_count == 0:
            sections = [
                Section(
                    name="Section 1: Intelligence Test (Cognitive Reasoning)",
                    description="Logical Reasoning, Numerical Reasoning, Verbal Reasoning, Abstract Reasoning",
                    order_index=1,
                    is_active=True
                ),
                Section(
                    name="Section 2: Aptitude Test",
                    description="Numerical Aptitude, Logical Aptitude, Verbal Aptitude, Spatial/Mechanical Aptitude",
                    order_index=2,
                    is_active=True
                ),
                Section(
                    name="Section 3: Study Habits",
                    description="Concentration, Consistency, Time Management, Exam Preparedness, Self-discipline",
                    order_index=3,
                    is_active=True
                ),
                Section(
                    name="Section 4: Learning Style",
                    description="Visual, Auditory, Reading/Writing, Kinesthetic",
                    order_index=4,
                    is_active=True
                ),
                Section(
                    name="Section 5: Career Interest (RIASEC)",
                    description="Realistic, Investigative, Artistic, Social, Enterprising, Conventional",
                    order_index=5,
                    is_active=True
                )
            ]
            for s in sections:
                db.add(s)
            db.commit()
            print(f"✅ Created {len(sections)} sections")
        else:
            # Ensure all 5 sections exist - create missing ones
            existing_sections = db.query(Section).order_by(Section.order_index).all()
            existing_order_indices = {s.order_index for s in existing_sections}
            
            # Define all 5 sections
            all_sections_config = [
                {"order_index": 1, "name": "Section 1: Intelligence Test (Cognitive Reasoning)", "description": "Logical Reasoning, Numerical Reasoning, Verbal Reasoning, Abstract Reasoning"},
                {"order_index": 2, "name": "Section 2: Aptitude Test", "description": "Numerical Aptitude, Logical Aptitude, Verbal Aptitude, Spatial/Mechanical Aptitude"},
                {"order_index": 3, "name": "Section 3: Study Habits", "description": "Concentration, Consistency, Time Management, Exam Preparedness, Self-discipline"},
                {"order_index": 4, "name": "Section 4: Learning Style", "description": "Visual, Auditory, Reading/Writing, Kinesthetic"},
                {"order_index": 5, "name": "Section 5: Career Interest (RIASEC)", "description": "Realistic, Investigative, Artistic, Social, Enterprising, Conventional"}
            ]
            
            # Create missing sections
            sections_to_create = []
            for config in all_sections_config:
                if config["order_index"] not in existing_order_indices:
                    sections_to_create.append(Section(
                        name=config["name"],
                        description=config["description"],
                        order_index=config["order_index"],
                        is_active=True
                    ))
            
            if sections_to_create:
                for s in sections_to_create:
                    db.add(s)
                db.commit()
                print(f"✅ Created {len(sections_to_create)} missing sections")
                # Refresh to get newly created sections with their IDs
                db.expire_all()
            else:
                print(f"ℹ️ All 5 sections already exist")
        
        # Seed questions - ensure each section has exactly 7 questions
        # Get all sections (refresh to include newly created ones)
        all_sections = db.query(Section).order_by(Section.order_index).all()
        print(f"🔵 Total sections in database: {len(all_sections)}")
        for s in all_sections:
            print(f"  - Section {s.order_index}: {s.name} (ID: {s.id})")
        
        # Ensure we have all 5 sections before creating questions
        if len(all_sections) < 5:
            print(f"⚠️ WARNING: Only {len(all_sections)} sections found, expected 5. Some sections may be missing.")
        
        # Check each section and ensure it has 7 questions
        for section in all_sections:
            print(f"🔵 Checking Section {section.order_index} ({section.name}) for questions...")
            section_question_count = db.query(Question).filter(
                Question.section_id == section.id,
                Question.is_active == True
            ).count()
            
            if section_question_count < 7:
                # Need to create questions for this section
                questions_to_create = 7 - section_question_count
                print(f"🔵 Section {section.order_index} ({section.name}) has {section_question_count} questions. Creating {questions_to_create} more...")
                
                # Generate questions based on section type
                new_questions = []
                for i in range(questions_to_create):
                    question_num = section_question_count + i + 1
                    
                    # Generate question text based on section
                    if section.order_index == 1:
                        # Intelligence Test questions
                        question_texts = [
                            "I can easily identify patterns in sequences",
                            "I enjoy solving mathematical problems",
                            "I can quickly understand complex instructions",
                            "I am good at logical reasoning",
                            "I can analyze problems from multiple angles",
                            "I enjoy brain teasers and puzzles",
                            "I can think abstractly"
                        ]
                    elif section.order_index == 2:
                        # Aptitude Test questions
                        question_texts = [
                            "I have strong numerical skills",
                            "I am good at spatial reasoning",
                            "I can quickly learn new skills",
                            "I have good mechanical aptitude",
                            "I am skilled at verbal reasoning",
                            "I can work with my hands effectively",
                            "I have good problem-solving abilities"
                        ]
                    elif section.order_index == 3:
                        # Study Habits questions
                        question_texts = [
                            "I maintain a consistent study schedule",
                            "I can concentrate for long periods",
                            "I manage my time effectively",
                            "I prepare well for exams",
                            "I have good self-discipline",
                            "I review my notes regularly",
                            "I avoid distractions while studying"
                        ]
                    elif section.order_index == 4:
                        # Learning Style questions
                        question_texts = [
                            "I learn best by seeing visual aids",
                            "I prefer listening to lectures",
                            "I learn by reading and writing",
                            "I learn best through hands-on activities",
                            "I remember things I see better than things I hear",
                            "I prefer audio recordings over written notes",
                            "I like to take detailed written notes"
                        ]
                    else:  # section.order_index == 5
                        # Career Interest (RIASEC) questions
                        question_texts = [
                            "I enjoy working with tools and machinery",
                            "I like to investigate and research",
                            "I enjoy creative and artistic activities",
                            "I like helping and teaching others",
                            "I enjoy leading and managing projects",
                            "I prefer structured and organized work",
                            "I like working outdoors"
                        ]
                    
                    # Use question text from list, or generate generic one
                    if question_num <= len(question_texts):
                        question_text = question_texts[question_num - 1]
                    else:
                        question_text = f"Question {question_num} for {section.name}"
                    
                    new_questions.append(Question(
                        question_text=question_text,
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        options="A) Strongly Disagree, B) Disagree, C) Neutral, D) Agree, E) Strongly Agree",
                        correct_answer="C",  # Default neutral answer
                        category=f"section_{section.order_index}",
                        section_id=section.id,
                        is_active=True,
                        order_index=question_num
                    ))
                
                # Add all new questions
                for q in new_questions:
                    db.add(q)
                db.commit()
                print(f"✅ Created {len(new_questions)} questions for Section {section.order_index}")
        
        # Final verification - ensure sections 4 and 5 exist and have questions
        section4 = db.query(Section).filter(Section.order_index == 4).first()
        section5 = db.query(Section).filter(Section.order_index == 5).first()
        
        if section4:
            section4_questions = db.query(Question).filter(Question.section_id == section4.id, Question.is_active == True).count()
            print(f"✅ Section 4: {section4_questions}/7 questions")
        else:
            print(f"❌ ERROR: Section 4 not found in database!")
        
        if section5:
            section5_questions = db.query(Question).filter(Question.section_id == section5.id, Question.is_active == True).count()
            print(f"✅ Section 5: {section5_questions}/7 questions")
        else:
            print(f"❌ ERROR: Section 5 not found in database!")
        
        # Final check
        total_questions = db.query(Question).count()
        print(f"ℹ️ Total questions in database: {total_questions}")

    except Exception as e:
        print(f"❌ Seed error: {e}")
        db.rollback()

    finally:
        db.close()


app.include_router(auth.router)
app.include_router(test_access.router)
app.include_router(test.router)
app.include_router(student_result.router)
app.include_router(counsellor_notes.router)
app.include_router(admin_analytics.router)


@app.get("/")
async def root():
    return {
        "message": "Career Profiling Platform API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=False
    )
