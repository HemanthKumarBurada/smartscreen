# SmartScreen — Intelligent Candidate Pre-Screening System
### MTech Final Year Project

---

## System Flow

```
Candidate submits Resume + Name + Email
        ↓
Score 1: Resume vs Job Description (semantic similarity)
        ↓
System emails candidate a unique LIVE RECORDING link (valid 48h)
        ↓
Candidate opens link → Records live self-intro (2–3 min)
        ↓
Score 2: Audio transcript vs Resume text (Whisper + NLP)
Score 3: Frame analysis — eye contact + malpractice detection
        ↓
Final Score = S1×W1 + S2×W2 + S3×W3
        ↓
Score ≥ 60% → QUALIFIED  |  Score < 60% → REJECTED
        ↓
HR views ranked results on dashboard
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend |
| Node.js | 18+ | Frontend |
| PostgreSQL | 14+ | Database |
| FFmpeg | Latest | Video audio extraction |
| Gmail account | - | Sending emails |

---

## Step-by-Step Setup (Local)

### Step 1 — Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql -c "CREATE DATABASE smartscreen_db;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"
```

**Windows:**
- Download from https://www.postgresql.org/download/windows/
- Install → open pgAdmin → create database `smartscreen_db`

**Mac:**
```bash
brew install postgresql
brew services start postgresql
psql postgres -c "CREATE DATABASE smartscreen_db;"
```

---

### Step 2 — Install FFmpeg

**Ubuntu:**
```bash
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

**Windows:**
- Download from https://ffmpeg.org/download.html
- Add to PATH

Verify: `ffmpeg -version`

---

### Step 3 — Set Up Gmail App Password

1. Go to your Gmail → **Settings** → **Security**
2. Enable **2-Step Verification** (required)
3. Go to **Security** → **App Passwords**
4. Select app: "Mail", device: "Other"
5. Copy the **16-character password** (format: xxxx xxxx xxxx xxxx)

---

### Step 4 — Configure Backend

```bash
cd smartscreen/backend

# Copy the example env file
cp .env.example .env

# Edit .env with your actual values
nano .env   # or use any text editor
```

Fill in `.env`:
```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/smartscreen_db
SECRET_KEY=any-random-32-character-string-here
MAIL_USERNAME=yourgmail@gmail.com
MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx    ← App Password (with dashes)
MAIL_FROM=yourgmail@gmail.com
APP_URL=http://localhost:3000
API_URL=http://localhost:8000
WHISPER_MODEL=base
```

---

### Step 5 — Install Backend Dependencies

```bash
cd smartscreen/backend

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows

# Install packages (takes 5–10 minutes, downloads ML models)
pip install -r requirements.txt
```

**Note:** First run downloads:
- `all-MiniLM-L6-v2` sentence transformer (~80MB)
- Whisper `base` model (~150MB)

---

### Step 6 — Run Backend

```bash
cd smartscreen/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Test: Open http://localhost:8000/docs → You should see Swagger API docs.

---

### Step 7 — Install and Run Frontend

Open a **new terminal**:

```bash
cd smartscreen/frontend
npm install
npm start
```

Frontend opens at http://localhost:3000

---

## URLs

| URL | Who uses it |
|-----|-------------|
| http://localhost:3000 | Candidate applies here |
| http://localhost:3000/record/{token} | Candidate opens from email |
| http://localhost:3000/hr | HR registers/logs in |
| http://localhost:8000/docs | API documentation |

---

## How HR Uses the System

1. Go to http://localhost:3000/hr
2. Click **Register** → enter name, company, email, password
3. Click **+ New Job**
4. Fill in:
   - Job title and description
   - Required skills (comma-separated, e.g.: `python, react, sql`)
   - Scoring weights (must sum to 100)
     - Technical role: Score1=50, Score2=30, Score3=20
     - Communication role: Score1=30, Score2=30, Score3=40
   - Qualifying threshold (default: 60%)
5. Click **Create**
6. Candidates now see this job on the apply page

---

## How Candidates Use the System

1. Go to http://localhost:3000
2. Select job position
3. Enter name and email
4. Upload resume (PDF or DOCX)
5. Submit → wait for email
6. Click link in email → browser opens live recording page
7. Allow camera + microphone permissions
8. Click **Start Recording** → give 2–3 min self-introduction
9. Preview → **Submit Video**
10. Receive result email within 2–5 minutes

---

## Scoring Explained

### Score 1 — Resume vs Job Description
- **Method:** Sentence-transformers semantic embedding (cosine similarity)
- **Formula:** 70% semantic score + 30% skill keyword overlap
- **When:** Runs immediately on resume submission

### Score 2 — Audio vs Resume
- **Method:** Whisper transcription → semantic similarity vs resume
- **Measures:** Whether candidate speaks about what they claim in resume
- **When:** After video upload

### Score 3 — Frame Behavior
- **Method:** OpenCV frame sampling (1 frame/sec)
- **Measures:**
  - Eye contact % (face centered in frame)
  - Malpractice flag (multiple faces detected → cap at 20%)
  - Speech fluency (words per minute from Whisper)
- **Formula:** 60% eye contact + 40% fluency

### Final Score
```
Final = (Score1 × W1 + Score2 × W2 + Score3 × W3) / 100
Qualified if Final ≥ qualifying_score (default 60%)
```

---

## Project Structure

```
smartscreen/
├── backend/
│   ├── app/
│   │   ├── main.py                     ← FastAPI app entry
│   │   ├── config.py                   ← Settings from .env
│   │   ├── api/
│   │   │   └── routes.py               ← All endpoints
│   │   ├── models/
│   │   │   ├── database.py             ← SQLAlchemy models
│   │   │   └── schemas.py              ← Pydantic schemas
│   │   ├── services/
│   │   │   ├── resume_parser.py        ← PDF/DOCX text extraction
│   │   │   ├── score1_resume_jd.py     ← Semantic similarity score
│   │   │   ├── score2_audio_resume.py  ← Whisper + NLP score
│   │   │   ├── score3_frame_behavior.py← OpenCV frame analysis
│   │   │   ├── final_aggregator.py     ← Weighted final score
│   │   │   └── email_service.py        ← Gmail SMTP emails
│   │   └── utils/
│   │       └── auth.py                 ← JWT + password hashing
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx                     ← Router
│   │   ├── index.js
│   │   ├── pages/
│   │   │   ├── ApplyPage.jsx           ← Candidate resume form
│   │   │   ├── RecordPage.jsx          ← Live video recording
│   │   │   └── HRDashboard.jsx         ← HR portal
│   │   └── services/
│   │       └── api.js                  ← Axios API calls
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Docker Setup (Alternative)

If you want to run everything with Docker:

```bash
cd smartscreen

# Copy and edit .env
cp backend/.env.example backend/.env
nano backend/.env   # fill in mail credentials

# Build and run
docker-compose up --build
```

All services start automatically.

---

## Troubleshooting

**Email not sending:**
- Use App Password (not Gmail login password)
- Enable 2-Step Verification first
- Check spam folder for test emails

**Whisper slow on first run:**
- Downloads ~150MB model on first use
- Set `WHISPER_MODEL=tiny` in .env for faster (less accurate) results

**Camera not working in browser:**
- Must use Chrome or Firefox
- Allow camera/microphone permissions when prompted
- localhost works; if using IP address, it must be HTTPS

**OpenCV face detection issues:**
- Ensure good lighting in candidate video
- Works best with frontal, well-lit face

**Database connection error:**
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify DATABASE_URL in .env matches your PostgreSQL credentials

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI (Python) |
| Database | PostgreSQL + SQLAlchemy |
| NLP / Similarity | sentence-transformers (all-MiniLM-L6-v2) |
| Speech-to-text | OpenAI Whisper (local, no API key) |
| Video Analysis | OpenCV (Haar cascade face detection) |
| Video Processing | MoviePy + FFmpeg |
| Email | aiosmtplib (Gmail SMTP) |
| Auth | JWT (python-jose) |
| Frontend | React 18 + React Router |
| HTTP Client | Axios |

---

*SmartScreen MTech Project — Intelligent Multi-Modal Candidate Pre-Screening System*
