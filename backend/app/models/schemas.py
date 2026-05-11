from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ─── HR Auth ──────────────────────────────────────────────
class HRRegister(BaseModel):
    email: EmailStr
    name: str
    company: str
    password: str

class HRLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# ─── Job ──────────────────────────────────────────────────
class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: str
    weight_score1: float = 35.0
    weight_score2: float = 25.0
    weight_score3: float = 20.0
    weight_score4: float = 20.0
    qualifying_score: float = 50.0

class JobOut(BaseModel):
    id: int
    title: str
    description: str
    required_skills: str
    weight_score1: float
    weight_score2: float
    weight_score3: float
    weight_score4: float
    qualifying_score: float
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# ─── Application ──────────────────────────────────────────
class ApplicationOut(BaseModel):
    id: int
    candidate_name: str
    candidate_email: str
    score1: Optional[float]
    score2: Optional[float]
    score3: Optional[float]
    score4: Optional[float]
    final_score: Optional[float]
    is_qualified: Optional[bool]
    status: str
    eye_contact_pct: Optional[float]
    malpractice_flag: bool
    transcript: Optional[str]
    created_at: datetime
    scored_at: Optional[datetime]
    missing_skills: Optional[str] = None
    class Config:
        from_attributes = True
