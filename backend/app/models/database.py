from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class HRUser(Base):
    __tablename__ = "hr_users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    company = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    jobs = relationship("Job", back_populates="hr")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    hr_id = Column(Integer, ForeignKey("hr_users.id"))
    title = Column(String)
    description = Column(Text)
    required_skills = Column(Text)  # comma-separated
    weight_score1 = Column(Float, default=35.0)   # resume vs JD
    weight_score2 = Column(Float, default=25.0)   # audio vs resume
    weight_score3 = Column(Float, default=20.0)   # frame behavior
    weight_score4 = Column(Float, default=20.0)   # add 4th weight
    qualifying_score = Column(Float, default=50.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    hr = relationship("HRUser", back_populates="jobs")
    applications = relationship("Application", back_populates="job")

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    candidate_name = Column(String)
    candidate_email = Column(String)
    resume_path = Column(String)
    resume_text = Column(Text)
    video_path = Column(String, nullable=True)
    video_token = Column(String, unique=True, index=True)  # for live recording link
    token_expires = Column(DateTime, nullable=True)
    score1 = Column(Float, nullable=True)
    score2 = Column(Float, nullable=True)
    score3 = Column(Float, nullable=True)
    score4 = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    missing_skills = Column(Text, nullable=True)
    is_qualified = Column(Boolean, nullable=True)
    status = Column(String, default="resume_submitted")  # resume_submitted | video_pending | video_received | scored | notified
    transcript = Column(Text, nullable=True)
    eye_contact_pct = Column(Float, nullable=True)
    malpractice_flag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    scored_at = Column(DateTime, nullable=True)
    job = relationship("Job", back_populates="applications")

def create_tables():
    Base.metadata.create_all(bind=engine)
