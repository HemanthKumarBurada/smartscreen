"""
Score 1: Semantic similarity between resume and job description.
70% document-level cosine similarity
30% skill overlap using direct full-text matching

FIX: Skills are now matched directly against the full resume text instead of
extracting skills from the resume first. The old approach split on delimiters
and filtered long sentences, causing skills that only appeared in experience
bullet points (e.g. "scheduling with Redis and Bull") to be silently dropped.

Matching strategies (in order):
1. Direct substring   — "redis" in full resume text
2. Fuzzy line match   — partial_ratio >= 85 on each resume line
3. Semantic embedding — cosine similarity >= 0.72 against resume sentences
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


def get_resume_lines(resume_text: str) -> list[str]:
    """
    Split resume into meaningful lines/chunks for fuzzy and semantic matching.
    Filters out blank lines and very short fragments.
    """
    lines = re.split(r'[\n\r•]', resume_text.lower())
    return [l.strip() for l in lines if len(l.strip()) > 3]


def match_skills_against_resume(
    jd_skills: list[str],
    resume_text: str,
    fuzzy_threshold: int = 85,
    semantic_threshold: float = 0.72,
) -> dict:
    """
    For each JD required skill, check whether it appears anywhere in the
    full resume text using 3 strategies.

    Strategy 1 — Direct substring:
        "redis" found in "scheduling with Redis and Bull for automated posting"
        Fast, zero false-positives for exact technology names.

    Strategy 2 — Fuzzy line match:
        partial_ratio("react.js", "built frontend using react js and typescript") >= 85
        Handles punctuation variants and minor typos.

    Strategy 3 — Semantic sentence match:
        Encodes each resume line and compares cosine similarity.
        Catches abbreviations: "ml" vs "machine learning", "k8s" vs "kubernetes".
    """
    if not jd_skills:
        return {"matched": [], "missing": [], "score": 0.0}

    model = get_model()
    resume_lower = resume_text.lower()
    resume_lines = get_resume_lines(resume_text)

    # Pre-encode resume lines once — reused for every JD skill in strategy 3
    line_embeddings = model.encode(resume_lines, convert_to_tensor=True) \
        if resume_lines else None

    matched = []
    missing = []

    for jd_skill in jd_skills:
        jd_clean = jd_skill.lower().strip()
        is_matched = False
        match_method = None

        # ── Strategy 1: Direct substring in full resume text ─────────────
        # Catches skills mentioned anywhere: skill sections, bullet points,
        # project descriptions, anywhere in the document.
        if jd_clean in resume_lower:
            is_matched = True
            match_method = "substring"

        # ── Strategy 2: Fuzzy match against each resume line ─────────────
        # Handles "react.js" vs "react js", "node.js" vs "nodejs", etc.
        if not is_matched:
            for line in resume_lines:
                if fuzz.partial_ratio(jd_clean, line) >= fuzzy_threshold:
                    is_matched = True
                    match_method = "fuzzy"
                    break

        # ── Strategy 3: Semantic match against resume lines ───────────────
        # Catches conceptual equivalents: "ml" vs "machine learning",
        # "k8s" vs "kubernetes", "rest" vs "restful apis".
        if not is_matched and line_embeddings is not None:
            jd_emb = model.encode(jd_clean, convert_to_tensor=True)
            sims = util.cos_sim(jd_emb, line_embeddings)[0]
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
        "score": round(score, 3),
    }


def compute_score1(
    resume_text: str,
    jd_text: str,
    required_skills: str,
) -> tuple[float, dict]:
    """
    Returns (score_out_of_100, skill_match_details)

    skill_match_details = {
        "matched": [...],   # JD skills found in resume
        "missing": [...],   # JD skills not found in resume
        "score":   0.0-1.0  # skill overlap ratio
    }
    """
    model = get_model()

    # ── 70%: Document-level semantic similarity ───────────────────────────
    emb_resume = model.encode(resume_text[:2000], convert_to_tensor=True)
    emb_jd     = model.encode(jd_text[:2000],     convert_to_tensor=True)
    semantic_sim   = float(util.cos_sim(emb_resume, emb_jd)[0][0])
    semantic_score = max(0.0, min(1.0, semantic_sim))

    # ── 30%: Skill-level matching ─────────────────────────────────────────
    # Parse HR-entered comma-separated required skills
    jd_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]

    # Match each JD skill directly against full resume text (not extracted tokens)
    skill_match = match_skills_against_resume(jd_skills, resume_text)
    skill_score = skill_match["score"]

    # ── Final score ───────────────────────────────────────────────────────
    final = (0.70 * semantic_score + 0.30 * skill_score) * 100
    final = round(min(final, 100.0), 2)

    print(f"[score1] semantic={semantic_score:.3f} | skill_overlap={skill_score:.3f} | final={final}")
    print(f"[score1] matched={skill_match['matched']}")
    print(f"[score1] missing={skill_match['missing']}")

    return final, skill_match