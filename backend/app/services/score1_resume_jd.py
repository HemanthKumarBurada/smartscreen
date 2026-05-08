"""
Score 1: Semantic similarity between resume and job description.
70% document-level cosine similarity
30% skill overlap using fuzzy + semantic matching

Handles real-world variations:
- java developer  vs  java
- react.js        vs  react
- scikit learn    vs  scikit-learn
- ml              vs  machine learning
- k8s             vs  kubernetes
- aws s3, ec2     vs  aws
"""

from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz
import re

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract skill-like tokens from any free-form text.
    No hardcoded keyword list — works on any domain.
    """
    text = text.lower().strip()

    stop_words = {
        "experience", "knowledge", "understanding", "proficiency",
        "ability", "skills", "years", "strong", "good", "excellent",
        "familiar", "working", "hands-on", "using", "with", "and",
        "or", "the", "a", "an", "of", "in", "to", "for", "on", "at",
        "is", "are", "was", "were", "be", "been", "have", "has", "had"
    }

    # Split on common delimiters used in skill lists and resumes
    raw_tokens = re.split(r'[,\n\r•\-\|/\(\)]', text)

    skills = []
    for token in raw_tokens:
        token = token.strip()
        # Remove leading/trailing punctuation and whitespace
        token = re.sub(r'^[\s\-•*·]+|[\s\-•*·]+$', '', token)

        # Skip if too short or too long
        if len(token) < 2 or len(token) > 40:
            continue

        # Skip pure stop words
        if token in stop_words:
            continue

        # Skip lines that look like full sentences (too many words = not a skill)
        if len(token.split()) > 5:
            continue

        # Skip lines that are mostly numbers
        if re.match(r'^\d+[\s\%\+]*$', token):
            continue

        if token:
            skills.append(token)

    return list(set(skills))


def match_skills_semantic(
    resume_skills: list[str],
    jd_skills: list[str],
    fuzzy_threshold: int = 80,
    semantic_threshold: float = 0.72
) -> dict:
    """
    Match resume skills against JD required skills using 4 strategies:

    1. Exact match           — "python" == "python"
    2. Substring match       — "java developer" contains "java"
    3. Fuzzy string match    — "react.js" ~= "react" (ratio >= 80)
    4. Semantic embedding    — "ml" ~= "machine learning" (cosine >= 0.72)
    """
    if not jd_skills:
        return {"matched": [], "missing": [], "score": 0.0}

    if not resume_skills:
        return {"matched": [], "missing": jd_skills, "score": 0.0}

    model = get_model()
    matched = []
    missing = []

    # Pre-encode all resume skills once for efficiency
    resume_embeddings = model.encode(resume_skills, convert_to_tensor=True)

    for jd_skill in jd_skills:
        jd_clean = jd_skill.lower().strip()
        is_matched = False
        match_method = None

        for r_skill in resume_skills:
            r_clean = r_skill.lower().strip()

            # Strategy 1: Exact match
            if jd_clean == r_clean:
                is_matched = True
                match_method = "exact"
                break

            # Strategy 2: Substring match (java dev contains java, aws s3 contains aws)
            if jd_clean in r_clean or r_clean in jd_clean:
                is_matched = True
                match_method = "substring"
                break

            # Strategy 3: Fuzzy match (react.js vs react, scikit-learn vs scikit learn)
            if fuzz.ratio(jd_clean, r_clean) >= fuzzy_threshold:
                is_matched = True
                match_method = "fuzzy"
                break

        # Strategy 4: Semantic match (ml vs machine learning, k8s vs kubernetes)
        if not is_matched:
            jd_emb = model.encode(jd_clean, convert_to_tensor=True)
            sims = util.cos_sim(jd_emb, resume_embeddings)[0]
            max_sim = float(sims.max())
            if max_sim >= semantic_threshold:
                is_matched = True
                match_method = "semantic"

        if is_matched:
            matched.append(jd_skill)
            print(f"[score1] MATCHED '{jd_skill}' via {match_method}")
        else:
            missing.append(jd_skill)
            print(f"[score1] MISSING '{jd_skill}'")

    score = len(matched) / len(jd_skills) if jd_skills else 0.0
    return {
        "matched": matched,
        "missing": missing,
        "score": round(score, 3)
    }


def compute_score1(
    resume_text: str,
    jd_text: str,
    required_skills: str
) -> tuple[float, dict]:
    """
    Returns (score_out_of_100, skill_match_details)

    skill_match_details = {
        "matched": [...],   # skills found in resume
        "missing": [...],   # skills not found in resume
        "score":   0.0-1.0  # skill overlap ratio
    }
    """
    model = get_model()

    # ── 70%: Document-level semantic similarity ──────────────────────────
    emb_resume = model.encode(resume_text[:2000], convert_to_tensor=True)
    emb_jd     = model.encode(jd_text[:2000],     convert_to_tensor=True)
    semantic_sim = float(util.cos_sim(emb_resume, emb_jd)[0][0])
    semantic_score = max(0.0, min(1.0, semantic_sim))

    # ── 30%: Skill-level matching ─────────────────────────────────────────
    # Extract skills from resume using NLP heuristics
    resume_skills = extract_skills_from_text(resume_text)

    # JD required skills come from the HR-entered comma-separated field
    jd_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]

    skill_match = match_skills_semantic(resume_skills, jd_skills)
    skill_score = skill_match["score"]

    # ── Final score ───────────────────────────────────────────────────────
    final = (0.70 * semantic_score + 0.30 * skill_score) * 100
    final = round(min(final, 100.0), 2)

    print(f"[score1] semantic={semantic_score:.3f} | skill_overlap={skill_score:.3f} | final={final}")
    print(f"[score1] matched={skill_match['matched']}")
    print(f"[score1] missing={skill_match['missing']}")

    return final, skill_match