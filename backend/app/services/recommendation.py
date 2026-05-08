"""
Recommendation Engine for SmartScreen.

Generates personalized, actionable improvement suggestions based on
actual candidate data — not just score thresholds.

Every recommendation is specific:
  - Names the exact missing skills
  - Cites the actual eye contact percentage
  - Quotes real WPM from the transcript
  - Identifies which resume skills were never mentioned verbally
  - Detects filler-heavy speech patterns
"""

import re
from typing import Optional


# ─── Helpers ──────────────────────────────────────────────────────────────────

FILLER_PATTERNS = [
    r'\bi know\b', r'\bi have experience\b', r'\bi am familiar\b',
    r'\bi worked with\b', r'\bi used\b', r'\bi learned\b',
    r'\bi can\b', r'\bbasically\b', r'\bkind of\b', r'\bsort of\b',
    r'\blike\b',  r'\bum+\b', r'\buh+\b', r'\bhmm+\b',
]


def _count_fillers(transcript: str) -> int:
    t = transcript.lower()
    return sum(len(re.findall(p, t)) for p in FILLER_PATTERNS)


def _wpm(transcript: str, duration_sec: float) -> float:
    if not transcript or duration_sec <= 0:
        return 0.0
    return len(transcript.split()) / duration_sec * 60


def _word_count(transcript: str) -> int:
    return len(transcript.split()) if transcript else 0


# ─── Main Recommendation Function ─────────────────────────────────────────────

def generate_recommendations(
    score1: float,
    score2: float,
    score3: float,
    score4: float,
    eye_contact_pct: float,
    malpractice_flag: bool,
    transcript: str,
    resume_text: str,
    job_required_skills: str,
    job_description: str,
    is_qualified: bool,
    duration_sec: float = 150.0,
    # Skill details from scoring pipeline (passed in from score1 + score2 results)
    s1_missing_skills: Optional[list] = None,
    s1_matched_skills: Optional[list] = None,
    s2_missing_skills: Optional[list] = None,   # skills on JD not spoken
    s4_missing_skills: Optional[list] = None,   # JD skills not addressed verbally
) -> list[str]:
    """
    Returns a list of specific, actionable recommendation strings.
    Every string references real data from this candidate's submission.
    """

    recs = []

    # ── Parse skill sets ──────────────────────────────────────────────────────
    jd_skills = [s.strip().lower() for s in job_required_skills.split(",") if s.strip()]
    resume_lower = resume_text.lower() if resume_text else ""
    transcript_lower = transcript.lower() if transcript else ""

    # ── SCORE 1: Resume vs JD ─────────────────────────────────────────────────
    if score1 < 75:
        if s1_missing_skills:
            top_missing = s1_missing_skills[:5]
            recs.append(
                f"📄 Resume Gap: Your resume is missing {len(s1_missing_skills)} required "
                f"skill(s) — specifically: {', '.join(top_missing)}. "
                f"Add these explicitly if you have experience with them."
            )
        elif jd_skills:
            # Fallback: compute manually
            missing = [s for s in jd_skills if s not in resume_lower]
            matched = [s for s in jd_skills if s in resume_lower]
            if missing:
                recs.append(
                    f"📄 Resume Gap: {len(missing)}/{len(jd_skills)} required skills "
                    f"are absent from your resume: {', '.join(missing[:5])}. "
                    f"Add these if applicable."
                )
            if matched and score1 < 55:
                recs.append(
                    f"📄 Matched {len(matched)} skills on your resume but your overall "
                    f"match score is still low ({score1:.0f}%). "
                    f"Add concrete project descriptions that use these skills in context."
                )

    # ── SCORE 2: Transcript vs Resume ─────────────────────────────────────────
    if score2 < 70 and transcript:
        # Find JD-required skills that appear in resume but were NOT spoken
        in_resume_not_spoken = []
        for skill in jd_skills:
            if skill in resume_lower and skill not in transcript_lower:
                in_resume_not_spoken.append(skill)

        if in_resume_not_spoken:
            recs.append(
                f"🎙️ Missed Key Skills: You listed "
                f"{', '.join(in_resume_not_spoken[:4])} on your resume "
                f"but never mentioned {'it' if len(in_resume_not_spoken) == 1 else 'them'} "
                f"in your video. Speak about the skills that matter most for this role."
            )
        elif s2_missing_skills:
            recs.append(
                f"🎙️ Resume Alignment: Your spoken introduction didn't reflect these "
                f"resume skills: {', '.join(s2_missing_skills[:4])}. "
                f"Walk through real projects where you applied these."
            )
        else:
            recs.append(
                f"🎙️ Resume Alignment ({score2:.0f}%): Your video didn't closely reflect "
                f"your written background. Walk through specific roles and projects "
                f"from your resume rather than speaking in general terms."
            )

    # ── SCORE 4: Transcript vs JD ─────────────────────────────────────────────
    if score4 < 70 and transcript:
        jd_skills_not_spoken = [s for s in jd_skills if s not in transcript_lower]
        if jd_skills_not_spoken:
            recs.append(
                f"📋 JD Alignment ({score4:.0f}%): The following skills from the job "
                f"description were not mentioned in your video: "
                f"{', '.join(jd_skills_not_spoken[:5])}. "
                f"Tailor your introduction to address what this specific role needs."
            )
        else:
            recs.append(
                f"📋 JD Alignment ({score4:.0f}%): Your video response didn't closely "
                f"address the job requirements. Study the JD and explicitly connect "
                f"your experience to the responsibilities listed."
            )

    # ── SCORE 3: Behavioral ───────────────────────────────────────────────────

    # Malpractice (highest priority)
    if malpractice_flag:
        recs.append(
            "🚨 Malpractice Detected: Multiple faces were visible during your recording. "
            "Record alone in a private room. Presence of others automatically lowers your score."
        )

    # Eye contact with real percentage
    elif eye_contact_pct < 40:
        recs.append(
            f"👁️ Eye Contact ({eye_contact_pct:.0f}% — aim for 70%+): "
            f"You were often looking away from the camera. "
            f"Look directly at the camera lens (not your preview on screen). "
            f"Place your camera at eye level and remove distractions from your field of view."
        )
    elif eye_contact_pct < 65:
        recs.append(
            f"👁️ Eye Contact ({eye_contact_pct:.0f}% — aim for 70%+): "
            f"Your gaze drifted frequently. Covering your self-preview with a sticky note "
            f"can help you focus on the lens."
        )

    # ── Speaking Pace (actual WPM) ────────────────────────────────────────────
    if transcript:
        actual_wpm = _wpm(transcript, duration_sec)
        wc = _word_count(transcript)

        if actual_wpm > 0:
            if actual_wpm < 80:
                recs.append(
                    f"🗣️ Pace Too Slow ({actual_wpm:.0f} WPM — ideal: 110–150): "
                    f"You spoke significantly slower than a natural conversational pace. "
                    f"Practice recording yourself and aim to sound energised and confident."
                )
            elif actual_wpm > 185:
                recs.append(
                    f"🗣️ Pace Too Fast ({actual_wpm:.0f} WPM — ideal: 110–150): "
                    f"You rushed through your introduction. Pause between points, "
                    f"breathe, and let each idea land before moving to the next."
                )

        # Response length
        if wc < 100:
            recs.append(
                f"⏱️ Too Short ({wc} words): A strong introduction covers your background, "
                f"key skills, and why you want this role — aim for 200–350 words (~2 min)."
            )
        elif wc > 520:
            recs.append(
                f"⏱️ Too Long ({wc} words): Keep your introduction under 3 minutes. "
                f"Focus on 2–3 key projects and your strongest qualifications."
            )

        # Filler / shallow speech detection
        filler_count = _count_fillers(transcript)
        filler_ratio = filler_count / max(wc / 20, 1)

        if filler_ratio > 2.5:
            recs.append(
                f"💬 Vague Language: Your transcript contains {filler_count} filler/shallow "
                f"phrases (e.g. 'I know', 'I have experience', 'basically'). "
                f"Replace them with specific examples: instead of 'I know Python', say "
                f"'I built a REST API with FastAPI that processed 10k requests/day.'"
            )

    # ── Positive note or summary ───────────────────────────────────────────────
    if not recs:
        recs.append(
            "✅ Excellent performance across all dimensions. "
            "Your resume, spoken content, and video behaviour were all well-aligned. "
            "Keep the same clarity and preparation in your next interview."
        )
    elif is_qualified:
        recs.insert(
            0,
            f"✅ You Qualified (score: {(score1+score2+score3+score4)/4:.0f}% avg)! "
            f"Here are targeted areas to sharpen further:"
        )
    else:
        recs.insert(
            0,
            "Here's specific feedback to improve your next application:"
        )

    return recs