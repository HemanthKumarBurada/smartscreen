import PyPDF2
import pdfplumber
import docx
import re
import os

SKILL_KEYWORDS = [
    "python","java","javascript","typescript","react","angular","vue","node","fastapi","django","flask",
    "sql","postgresql","mysql","mongodb","redis","docker","kubernetes","git","aws","azure","gcp",
    "machine learning","deep learning","tensorflow","pytorch","nlp","computer vision","data science",
    "scikit-learn","pandas","numpy","matplotlib","seaborn","tableau","power bi",
    "c++","c#","rust","golang","php","ruby","swift","kotlin","flutter","react native",
    "rest api","graphql","microservices","ci/cd","devops","agile","scrum",
    "html","css","bootstrap","tailwind","linux","bash","selenium","opencv","spark","hadoop"
]

def extract_text_from_pdf(path: str) -> str:
    text = ""

    # --- Method 1: pdfplumber (best for most modern PDFs) ---
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            print(f"[resume_parser] pdfplumber extracted {len(text)} chars from {os.path.basename(path)}")
            return text
        else:
            print(f"[resume_parser] pdfplumber returned empty, trying PyPDF2...")
    except Exception as e:
        print(f"[resume_parser] pdfplumber failed: {e}, trying PyPDF2...")

    # --- Method 2: PyPDF2 fallback ---
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            print(f"[resume_parser] PyPDF2 extracted {len(text)} chars from {os.path.basename(path)}")
            return text
        else:
            print(f"[resume_parser] PyPDF2 also returned empty — PDF may be scanned/image-based")
    except Exception as e:
        print(f"[resume_parser] PyPDF2 failed: {e}")

    return text


def extract_text_from_docx(path: str) -> str:
    try:
        doc = docx.Document(path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n".join(paragraphs)
        print(f"[resume_parser] docx extracted {len(text)} chars from {os.path.basename(path)}")
        return text
    except Exception as e:
        print(f"[resume_parser] docx extraction failed: {e}")
        return ""


def extract_resume_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    print(f"[resume_parser] Extracting text from: {os.path.basename(path)} (type: {ext})")

    if ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]:
        text = extract_text_from_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not text.strip():
        print(f"[resume_parser] WARNING: No text extracted from {os.path.basename(path)}")
    else:
        print(f"[resume_parser] SUCCESS: {len(text)} total chars, first 100: {text[:100].strip()!r}")

    return text


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found = [skill for skill in SKILL_KEYWORDS if skill in text_lower]
    return list(set(found))


def extract_email_from_text(text: str) -> str:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group() if match else ""


def extract_name_from_text(text: str) -> str:
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines[0] if lines else "Candidate"