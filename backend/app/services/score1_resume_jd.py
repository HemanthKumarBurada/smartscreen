"""
Score 1: Semantic similarity between resume text and job description.
70% semantic cosine similarity + 30% skill keyword overlap
"""
from sentence_transformers import SentenceTransformer, util
from app.services.resume_parser import extract_skills

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def compute_score1(resume_text: str, jd_text: str, required_skills: str) -> float:
    model = get_model()

    # Semantic similarity
    emb_resume = model.encode(resume_text[:2000], convert_to_tensor=True)
    emb_jd = model.encode(jd_text[:2000], convert_to_tensor=True)
    semantic_sim = float(util.cos_sim(emb_resume, emb_jd)[0][0])
    semantic_score = max(0.0, min(1.0, semantic_sim))

    # Skill overlap
    resume_skills = set(extract_skills(resume_text))
    jd_skills = set([s.strip().lower() for s in required_skills.split(",")])
    if jd_skills:
        matched = resume_skills & jd_skills
        skill_score = len(matched) / len(jd_skills)
    else:
        skill_score = semantic_score

    final = (0.70 * semantic_score + 0.30 * skill_score) * 100
    return round(min(final, 100.0), 2)
