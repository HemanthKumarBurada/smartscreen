"""
Score 2: Audio Transcript vs Resume  (score2)
Score 4: Audio Transcript vs JD      (score4)

Uses Whisper for transcription.
Then applies the SAME direct full-text matching strategy as the updated Score 1:
  - 70% semantic document-level cosine similarity
  - 30% skill overlap via direct substring + fuzzy + semantic matching

FIX: Skills are now matched directly against the full transcript text instead of
extracting skill tokens from the transcript first. The old approach split on
delimiters and filtered long sentences, so skills only mentioned in natural
speech ("I have worked with Redis for job queuing") were silently dropped.
"""

import whisper
import os
import re
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


# ─── Transcript Line Splitter ─────────────────────────────────────────────────

def get_transcript_lines(transcript: str) -> list[str]:
    """
    Split transcript into sentence-level chunks for fuzzy and semantic matching.
    Whisper transcripts are mostly punctuation-separated sentences.
    """
    lines = re.split(r'[.\n\r,]', transcript.lower())
    return [l.strip() for l in lines if len(l.strip()) > 3]


# ─── Skill Matching Against Full Transcript ───────────────────────────────────

def match_skills_in_transcript(
    target_skills: list[str],
    transcript: str,
    fuzzy_threshold: int = 85,
    semantic_threshold: float = 0.72,
) -> dict:
    """
    For each target skill (from JD required skills), check whether the candidate
    mentioned it anywhere in their spoken transcript using 3 strategies.

    Strategy 1 — Direct substring:
        "redis" found in "i have worked with redis for job queuing"
        Handles skills mentioned naturally in speech.

    Strategy 2 — Fuzzy line match:
        partial_ratio("react.js", "i built the frontend in react js") >= 85
        Handles spoken pronunciation variants and minor transcription errors.

    Strategy 3 — Semantic sentence match:
        Encodes transcript sentences and compares cosine similarity.
        Catches abbreviations: "ml" vs "machine learning", "nlp" vs "natural language processing".
    """
    if not target_skills:
        return {"matched": [], "missing": [], "score": 0.0}

    model = get_st_model()
    transcript_lower = transcript.lower()
    transcript_lines = get_transcript_lines(transcript)

    # Pre-encode transcript lines once — reused for every skill in strategy 3
    line_embeddings = model.encode(transcript_lines, convert_to_tensor=True) \
        if transcript_lines else None

    matched = []
    missing = []

    for skill in target_skills:
        skill_clean = skill.lower().strip()
        is_matched = False
        match_method = None

        # ── Strategy 1: Direct substring in full transcript ───────────────
        # Catches skills spoken naturally anywhere in the transcript.
        if skill_clean in transcript_lower:
            is_matched = True
            match_method = "substring"

        # ── Strategy 2: Fuzzy match against transcript sentences ──────────
        # Handles transcription errors: "nest js" vs "nestjs", "type script" vs "typescript"
        if not is_matched:
            for line in transcript_lines:
                if fuzz.partial_ratio(skill_clean, line) >= fuzzy_threshold:
                    is_matched = True
                    match_method = "fuzzy"
                    break

        # ── Strategy 3: Semantic match against transcript sentences ───────
        # Catches conceptual equivalents spoken differently:
        # "rest apis" vs "restful", "postgres" vs "postgresql"
        if not is_matched and line_embeddings is not None:
            skill_emb = model.encode(skill_clean, convert_to_tensor=True)
            sims = util.cos_sim(skill_emb, line_embeddings)[0]
            max_sim = float(sims.max())
            if max_sim >= semantic_threshold:
                is_matched = True
                match_method = "semantic"

        if is_matched:
            matched.append(skill)
            print(f"[skill_match] MATCHED '{skill}' via {match_method}")
        else:
            missing.append(skill)
            print(f"[skill_match] MISSING '{skill}'")

    score = len(matched) / len(target_skills) if target_skills else 0.0
    return {"matched": matched, "missing": missing, "score": round(score, 3)}


# ─── Single Score Computation ─────────────────────────────────────────────────

def _compute_single_score(
    transcript: str,
    target_text: str,
    target_skills: list[str],
    label: str = "score",
) -> tuple[float, dict]:
    """
    Compute a single score (transcript vs target text).

    70% — document-level cosine similarity (how related the speech is to the target)
    30% — skill overlap (how many required skills were actually mentioned)

    Returns (score_0_to_100, details_dict)
    """
    model = get_st_model()

    # 70% — document-level cosine similarity
    emb_transcript = model.encode(transcript[:2000], convert_to_tensor=True)
    emb_target     = model.encode(target_text[:2000], convert_to_tensor=True)
    semantic_sim   = float(util.cos_sim(emb_transcript, emb_target)[0][0])
    semantic_sim   = max(0.0, min(1.0, semantic_sim))

    # 30% — match required skills directly against full transcript text
    skill_result = match_skills_in_transcript(target_skills, transcript)

    final = (0.70 * semantic_sim + 0.30 * skill_result["score"]) * 100

    print(f"[{label}] semantic={semantic_sim:.2f}  skill_overlap={skill_result['score']:.2f}")
    print(f"[{label}] matched: {skill_result['matched']}")
    print(f"[{label}] missing: {skill_result['missing']}")

    return round(min(final, 100.0), 2), skill_result


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def compute_score2(
    video_path: str,
    resume_text: str,
    jd_text: str = "",
    required_skills: str = "",
) -> tuple[float, float, str, dict, dict]:
    """
    Main entry point.

    Returns:
        score2     : transcript vs resume  (0–100)
        score4     : transcript vs JD      (0–100)
        transcript : full Whisper transcript text
        s2_details : matched/missing skills for score2
        s4_details : matched/missing skills for score4
    """
    try:
        result     = extract_audio_and_transcribe(video_path)
        transcript = result["text"].strip()

        print(f"[score2] transcript length: {len(transcript)} chars")
        print(f"[score2] transcript preview: {transcript[:120]!r}")

        if not transcript:
            empty = {"matched": [], "missing": [], "score": 0.0}
            return 0.0, 0.0, "", empty, empty

        # Parse required skills once — used for both score2 and score4
        jd_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]

        # ── Score 2: transcript vs resume ─────────────────────────────────
        # Checks whether what the candidate *said* aligns with their resume
        # and covers the skills the JD requires.
        score2, s2_details = _compute_single_score(
            transcript, resume_text, jd_skills, label="score2"
        )

        # ── Score 4: transcript vs JD ──────────────────────────────────────
        # Checks whether the candidate's speech is relevant to the job description.
        score4     = 0.0
        s4_details = {"matched": [], "missing": [], "score": 0.0}

        if jd_text:
            score4, s4_details = _compute_single_score(
                transcript, jd_text, jd_skills, label="score4"
            )

        return score2, score4, transcript, s2_details, s4_details

    except Exception as e:
        print(f"[score2/4] ERROR: {e}")
        empty = {"matched": [], "missing": [], "score": 0.0}
        return 0.0, 0.0, f"Error: {str(e)}", empty, empty