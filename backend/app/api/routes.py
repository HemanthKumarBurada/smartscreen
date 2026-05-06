from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import shutil, os, uuid

from app.models.database import get_db, HRUser, Job, Application
from app.models.schemas import HRRegister, HRLogin, Token, JobCreate, JobOut, ApplicationOut
from app.utils.auth import hash_password, verify_password, create_access_token, decode_token, generate_video_token
from app.services.resume_parser import extract_resume_text, extract_skills
from app.services.score1_resume_jd import compute_score1
from app.services.score2_audio_resume import compute_score2
from app.services.score3_frame_behavior import compute_score3
from app.services.final_aggregator import compute_final_score
from app.services.email_service import send_recording_link, send_result_email
from app.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/hr/login")
UPLOAD_DIR = "uploads"
RESUME_DIR = os.path.join(UPLOAD_DIR, "resumes")
VIDEO_DIR  = os.path.join(UPLOAD_DIR, "videos")

os.makedirs(RESUME_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR,  exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_current_hr(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> HRUser:
    try:
        payload = decode_token(token)
        hr = db.query(HRUser).filter(HRUser.id == int(payload["sub"])).first()
        if not hr:
            raise HTTPException(status_code=401, detail="Invalid token")
        return hr
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

def run_video_pipeline(app_id: int, db_url: str):
    """Background task: score video after upload."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(db_url)
    DBSession = sessionmaker(bind=engine)
    db = DBSession()
    try:
        app = db.query(Application).filter(Application.id == app_id).first()
        if not app or not app.video_path:
            return
        job = db.query(Job).filter(Job.id == app.job_id).first()

        # Score 2
        score2, score4, transcript = compute_score2(
         app.video_path, app.resume_text or "", job.description or ""
)
        # Score 3
        score3, frame_data = compute_score3(app.video_path, transcript)
        # Final
        result = compute_final_score(
    app.score1 or 0, score2, score3, score4,
    job.weight_score1, job.weight_score2, job.weight_score3, job.weight_score4,
    job.qualifying_score, frame_data.get("malpractice_flag", False)
)

        app.score2 = score2
        app.score3 = score3
        app.score4 = score4
        app.final_score = result["final_score"]
        app.is_qualified = result["is_qualified"]
        app.transcript = transcript
        app.eye_contact_pct = frame_data.get("eye_contact_pct")
        app.malpractice_flag = frame_data.get("malpractice_flag", False)
        app.status = "scored"
        app.scored_at = datetime.now(timezone.utc)
        db.commit()

        # Send result email (sync wrapper)
        import asyncio
        asyncio.run(send_result_email(
            app.candidate_name, app.candidate_email,
            job.title, result["final_score"], result["is_qualified"]
        ))
        app.status = "notified"
        db.commit()
    except Exception as e:
        print(f"Pipeline error for app {app_id}: {e}")
    finally:
        db.close()

# ─── HR Auth ──────────────────────────────────────────────────────────────────
@router.post("/hr/register", response_model=Token)
def hr_register(data: HRRegister, db: Session = Depends(get_db)):
    if db.query(HRUser).filter(HRUser.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    hr = HRUser(email=data.email, name=data.name, company=data.company,
                hashed_password=hash_password(data.password))
    db.add(hr); db.commit(); db.refresh(hr)
    return {"access_token": create_access_token({"sub": str(hr.id)}), "token_type": "bearer"}

@router.post("/hr/login", response_model=Token)
def hr_login(data: HRLogin, db: Session = Depends(get_db)):
    hr = db.query(HRUser).filter(HRUser.email == data.email).first()
    if not hr or not verify_password(data.password, hr.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_access_token({"sub": str(hr.id)}), "token_type": "bearer"}

@router.get("/hr/me")
def hr_me(hr: HRUser = Depends(get_current_hr)):
    return {"id": hr.id, "name": hr.name, "email": hr.email, "company": hr.company}

# ─── Jobs ─────────────────────────────────────────────────────────────────────
@router.post("/jobs", response_model=JobOut)
def create_job(data: JobCreate, hr: HRUser = Depends(get_current_hr), db: Session = Depends(get_db)):
    total = data.weight_score1 + data.weight_score2 + data.weight_score3 + data.weight_score4  # ← include w4
    if abs(total - 100) > 0.1:
        raise HTTPException(400, "Weights must sum to 100")
    job = Job(hr_id=hr.id, **data.model_dump())
    db.add(job); db.commit(); db.refresh(job)
    return job

@router.get("/jobs", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.is_active == True).all()

@router.get("/jobs/my", response_model=list[JobOut])
def my_jobs(hr: HRUser = Depends(get_current_hr), db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.hr_id == hr.id).all()

@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def get_applications(job_id: int, hr: HRUser = Depends(get_current_hr), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.hr_id == hr.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return db.query(Application).filter(Application.job_id == job_id)\
             .order_by(Application.final_score.desc().nullslast()).all()

# ─── Candidate Apply ──────────────────────────────────────────────────────────
@router.post("/apply")
async def apply(
    background_tasks: BackgroundTasks,
    job_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(404, "Job not found")

    # Save resume file
    ext = os.path.splitext(resume.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    resume_path = os.path.join(RESUME_DIR, filename)
    with open(resume_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # Parse resume
    try:
        resume_text = extract_resume_text(resume_path)
    except Exception as e:
        raise HTTPException(400, f"Could not parse resume: {e}")

    # Debug log
    print(f"[apply] resume_text length: {len(resume_text)}")
    print(f"[apply] resume_text preview: {resume_text[:100]!r}")

    if not resume_text.strip():
        raise HTTPException(400, "Could not extract text from resume. Please upload a text-based PDF or DOCX.")

    # Score 1
    score1 = compute_score1(resume_text, job.description, job.required_skills)
    print(f"[apply] score1: {score1}")

    # Create application
    token = generate_video_token()
    job_title = job.title  # capture before session closes

    app = Application(
        job_id=job_id,
        candidate_name=name,
        candidate_email=email,
        resume_path=resume_path,
        resume_text=resume_text,          # ← explicitly set
        video_token=token,
        token_expires=datetime.utcnow() + timedelta(hours=48),
        score1=score1,
        status="resume_submitted"
    )
    db.add(app)
    db.commit()
    db.refresh(app)  # ← reload from DB to confirm it was saved

    # Confirm resume_text was actually saved
    print(f"[apply] saved app.id={app.id}, resume_text length in DB: {len(app.resume_text or '')}")

    # Send email in background (no db access here)
    background_tasks.add_task(
        lambda: __import__('asyncio').run(
            send_recording_link(name, email, token, job_title)
        )
    )

    return {
        "message": "Resume received! Check your email for the video recording link.",
        "application_id": app.id,
        "score1": score1
    }

# ─── Video Recording ──────────────────────────────────────────────────────────
@router.get("/record/{token}")
def get_record_info(token: str, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.video_token == token).first()
    if not app:
        raise HTTPException(404, "Invalid recording link")
    if app.token_expires and datetime.utcnow() > app.token_expires:
        raise HTTPException(410, "Recording link has expired")
    if app.video_path:
        raise HTTPException(409, "Video already submitted")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    return {
        "candidate_name": app.candidate_name,
        "job_title": job.title if job else "Position",
        "instructions": "Record a 2–3 minute self-introduction. Speak about your background, skills, and experience."
    }

@router.post("/record/{token}/upload")
async def upload_video(
    token: str,
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.video_token == token).first()
    if not app:
        raise HTTPException(404, "Invalid token")
    if app.token_expires and datetime.utcnow() > app.token_expires:
        raise HTTPException(410, "Link expired")
    if app.video_path:
        raise HTTPException(409, "Video already submitted")

    # Save video
    ext = os.path.splitext(video.filename)[1] or ".webm"
    filename = f"video_{uuid.uuid4()}{ext}"
    video_path = os.path.join(VIDEO_DIR, filename)
    with open(video_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    app.video_path = video_path
    app.status = "video_received"
    db.commit()

    # Run scoring pipeline in background
    background_tasks.add_task(run_video_pipeline, app.id, settings.DATABASE_URL)

    return {"message": "Video received! You will get your result by email within a few minutes."}
