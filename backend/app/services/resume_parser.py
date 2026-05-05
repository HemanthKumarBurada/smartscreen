import PyPDF2
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
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_resume_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

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
