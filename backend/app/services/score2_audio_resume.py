"""
Score 2: Audio Transcript vs Resume  (score2)
Score 4: Audio Transcript vs JD      (score4)

Uses Whisper for transcription.
Then applies the SAME 3-layer matching strategy as Score 1:
  - 70% semantic document-level cosine similarity
  - 30% skill overlap via exact + fuzzy + semantic matching

This ensures consistency across all scores and eliminates the raw-cosine-only weakness.
"""

import whisper
import os
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz
from app.config import settings

_whisper_model = None
_st_model = None


# ─── Model Loading ────────────────────────────────────────────────────────────

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(settings.WHISPER_MODEL)
    return _whisper_model


def get_st_model():
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


# ─── Audio Extraction & Transcription ─────────────────────────────────────────

def extract_audio_and_transcribe(video_path: str) -> dict:
    """Extract audio from video and transcribe using Whisper."""
    import moviepy.editor as mp

    audio_path = video_path.replace(".webm", ".wav").replace(".mp4", ".wav")
    if not audio_path.endswith(".wav"):
        audio_path = video_path + ".wav"

    clip = mp.VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
    clip.close()

    model = get_whisper()
    result = model.transcribe(audio_path)

    if os.path.exists(audio_path):
        os.remove(audio_path)

    return {
        "text": result["text"],
        "segments": result.get("segments", [])
    }


# ─── Skill Extraction from Text ───────────────────────────────────────────────

def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract skill-like tokens from free text (resume or transcript).
    No hardcoded list — works for any domain.
    Mirrors the same function in score1_resume_jd.py.
    """
    import re

    text = text.lower().strip()

    stop_words = {
        "experience", "knowledge", "understanding", "proficiency",
        "ability", "skills", "years", "strong", "good", "excellent",
        "familiar", "working", "hands-on", "using", "with", "and", "or",
        "the", "a", "an", "in", "of", "for", "to", "is", "was", "my",
        "i", "we", "have", "had", "been", "am", "are", "also", "as"
    }

    # Split on delimiters common in resumes and job descriptions
    raw_tokens = re.split(r'[,\n\r•\-\|/]', text)

    skills = []
    for token in raw_tokens:
        token = re.sub(r'^[\s\-•*]+|[\s\-•*]+$', '', token.strip())
        if len(token) < 2 or len(token) > 40:
            continue
        if token in stop_words:
            continue
        if len(token.split()) > 5:
            continue
        if token:
            skills.append(token)

    return list(set(skills))


# ─── Skill Matching (exact + fuzzy + semantic) ────────────────────────────────

def match_skills_in_transcript(
    spoken_skills: list[str],
    target_skills: list[str],
    fuzzy_threshold: int = 78,
    semantic_threshold: float = 0.72
) -> dict:
    """
    Match skills spoken in transcript against target skills (resume or JD).
    3-layer matching — same approach as Score 1.

    spoken_skills  : skills extracted from Whisper transcript
    target_skills  : skills from resume or JD to match against
    """
    if not target_skills:
        return {"matched": [], "missing": [], "score": 0.0}

    model = get_st_model()
    matched = []
    missing = []

    spoken_embeddings = model.encode(spoken_skills, convert_to_tensor=True) \
        if spoken_skills else None

    for target_skill in target_skills:
        ts = target_skill.lower().strip()
        is_matched = False

        for spoken in spoken_skills:
            sp = spoken.lower().strip()

            # Layer 1: exact match
            if ts == sp:
                is_matched = True
                break

            # Layer 2: substring (java developer contains java)
            if ts in sp or sp in ts:
                is_matched = True
                break

            # Layer 3: fuzzy (react.js ↔ react, scikit-learn ↔ scikit learn)
            if fuzz.ratio(ts, sp) >= fuzzy_threshold:
                is_matched = True
                break

        # Layer 4: semantic (ml ↔ machine learning, k8s ↔ kubernetes)
        if not is_matched and spoken_embeddings is not None and len(spoken_skills) > 0:
            target_emb = model.encode(ts, convert_to_tensor=True)
            sims = util.cos_sim(target_emb, spoken_embeddings)[0]
            if float(sims.max()) >= semantic_threshold:
                is_matched = True

        if is_matched:
            matched.append(target_skill)
        else:
            missing.append(target_skill)

    score = len(matched) / len(target_skills) if target_skills else 0.0
    return {"matched": matched, "missing": missing, "score": score}


# ─── Score Computation ────────────────────────────────────────────────────────

def _compute_single_score(
    transcript: str,
    target_text: str,
    target_skills: list[str],
    label: str = "score"
) -> tuple[float, dict]:
    """
    Compute a single score (transcript vs target).

    70% document-level semantic similarity
    30% skill overlap (exact + fuzzy + semantic)

    Returns (score_0_to_100, details_dict)
    """
    model = get_st_model()

    # 70% — document-level cosine similarity
    emb_transcript = model.encode(transcript[:2000], convert_to_tensor=True)
    emb_target     = model.encode(target_text[:2000], convert_to_tensor=True)
    semantic_sim   = float(util.cos_sim(emb_transcript, emb_target)[0][0])
    semantic_sim   = max(0.0, min(1.0, semantic_sim))

    # 30% — skill-level match
    spoken_skills = extract_skills_from_text(transcript)
    skill_result  = match_skills_in_transcript(spoken_skills, target_skills)

    final = (0.70 * semantic_sim + 0.30 * skill_result["score"]) * 100

    print(f"[{label}] semantic={semantic_sim:.2f}  skill_overlap={skill_result['score']:.2f}")
    print(f"[{label}] spoken skills: {spoken_skills[:8]}")
    print(f"[{label}] matched: {skill_result['matched']}")
    print(f"[{label}] missing: {skill_result['missing']}")

    return round(min(final, 100.0), 2), skill_result


def compute_score2(
    video_path: str,
    resume_text: str,
    jd_text: str = "",
    required_skills: str = ""
) -> tuple[float, float, str, dict, dict]:
    """
    Main entry point.

    Returns:
        score2          : transcript vs resume  (0–100)
        score4          : transcript vs JD      (0–100)
        transcript      : full Whisper transcript text
        s2_details      : matched/missing skills for score2
        s4_details      : matched/missing skills for score4
    """
    try:
        result      = extract_audio_and_transcribe(video_path)
        transcript  = result["text"].strip()

        print(f"[score2] transcript length: {len(transcript)} chars")
        print(f"[score2] transcript preview: {transcript[:120]!r}")

        if not transcript:
            empty = {"matched": [], "missing": [], "score": 0.0}
            return 0.0, 0.0, "", empty, empty

        # ── Score 2: transcript vs resume ────────────────────────────────
        # Use JD required_skills as the skill set to check coverage in spoken content
        # (candidate should verbally confirm skills on their resume that the JD cares about)
        resume_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()] \
                        if required_skills else extract_skills_from_text(resume_text)

        score2, s2_details = _compute_single_score(
            transcript, resume_text, resume_skills, label="score2"
        )

        # ── Score 4: transcript vs JD ─────────────────────────────────────
        score4     = 0.0
        s4_details = {"matched": [], "missing": [], "score": 0.0}

        if jd_text:
            jd_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]
            score4, s4_details = _compute_single_score(
                transcript, jd_text, jd_skills, label="score4"
            )

        return score2, score4, transcript, s2_details, s4_details

    except Exception as e:
        print(f"[score2/4] ERROR: {e}")
        empty = {"matched": [], "missing": [], "score": 0.0}
        return 0.0, 0.0, f"Error: {str(e)}", empty, empty