"""
Score 3: Video frame behavioral analysis.
- Eye contact % (face centered in frame)
- Malpractice detection (multiple faces = flag)
- Communication fluency from transcript

FIXES:
1. Eye contact is now calculated only over frames where a face was detected.
   Previously, no-face frames counted against the candidate in the denominator,
   unfairly penalizing brief head movements or lighting issues.

2. Fluency falls back to neutral (0.5) when the transcript is suspiciously short
   relative to video duration (likely a transcription failure, not a silent candidate).
   Previously, a 2-word Whisper output would give 0.3 fluency and tank the score.

3. ffprobe fix retained: Browser WebM files report fps=1000 via OpenCV.
   We use ffprobe to get actual frame count and real FPS.
"""

import cv2
import subprocess
import json
import os

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


# ─── FPS & Duration ───────────────────────────────────────────────────────────

def get_real_fps_and_duration(video_path: str) -> tuple[float, float]:
    """
    OpenCV reports fps=1000 for browser-recorded WebM files.
    Use ffprobe to count actual frames and get real duration.
    Falls back to OpenCV values if ffprobe is unavailable.
    """
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ], capture_output=True, text=True, timeout=30)

        fmt = json.loads(result.stdout).get('format', {})
        duration = float(fmt.get('duration', 0))

        if duration <= 0:
            raise ValueError("No duration from ffprobe")

        frame_result = subprocess.run([
            'ffprobe', '-v', 'error',
            '-count_frames',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_read_frames',
            '-of', 'default=nokey=1:noprint_wrappers=1',
            video_path
        ], capture_output=True, text=True, timeout=60)

        actual_frames = int(frame_result.stdout.strip())
        real_fps = actual_frames / duration if duration > 0 else 25.0

        print(f"[score3] ffprobe: duration={duration:.1f}s frames={actual_frames} real_fps={real_fps:.2f}")
        return real_fps, duration

    except Exception as e:
        print(f"[score3] ffprobe failed ({e}), falling back to OpenCV")
        cap = cv2.VideoCapture(video_path)
        raw_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        fps = raw_fps if raw_fps < 120 else 25.0
        duration = total_frames / raw_fps if raw_fps > 0 else 0
        print(f"[score3] OpenCV fallback: raw_fps={raw_fps} using fps={fps} duration={duration:.1f}s")
        return fps, duration


# ─── Frame Analysis ───────────────────────────────────────────────────────────

def analyze_frames(video_path: str) -> dict:
    real_fps, duration_sec = get_real_fps_and_duration(video_path)

    sample_interval = max(1, int(real_fps))

    cap = cv2.VideoCapture(video_path)
    frame_idx = 0
    analyzed = 0
    eye_contact_frames = 0
    malpractice_frames = 0
    no_face_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )
            analyzed += 1

            if len(faces) == 0:
                no_face_frames += 1
                print(f"[score3] sec~{analyzed}: no face detected")

            elif len(faces) == 1:
                h, w = frame.shape[:2]
                (x, y, fw, fh) = faces[0]
                face_cx = x + fw // 2
                frame_cx = w // 2
                offset = abs(face_cx - frame_cx) / (w / 2)
                in_contact = offset < 0.35
                if in_contact:
                    eye_contact_frames += 1
                print(f"[score3] sec~{analyzed}: offset={offset:.2f} eye_contact={in_contact}")

            else:
                malpractice_frames += 1
                print(f"[score3] sec~{analyzed}: multiple faces ({len(faces)}) — malpractice")

        frame_idx += 1

    cap.release()

    if analyzed == 0:
        print("[score3] WARNING: No frames were analyzed")
        return {
            "eye_contact_pct":  0.0,
            "malpractice_flag": False,
            "malpractice_pct":  0.0,
            "no_face_pct":      0.0,
            "frames_analyzed":  0,
            "duration_sec":     duration_sec,
        }

    # ── FIX: calculate eye contact only over frames where a face was present ──
    # Old: eye_contact_frames / analyzed  (no-face frames unfairly in denominator)
    # New: eye_contact_frames / face_frames (only judge when candidate is visible)
    face_frames     = analyzed - no_face_frames
    eye_contact_pct = (eye_contact_frames / face_frames * 100) if face_frames > 0 else 0.0
    malpractice_pct = malpractice_frames / analyzed * 100
    no_face_pct     = no_face_frames / analyzed * 100
    malpractice_flag = malpractice_pct > 10

    print(f"[score3] analyzed={analyzed} face_frames={face_frames} "
          f"eye_contact={eye_contact_pct:.1f}% "
          f"no_face={no_face_pct:.1f}% malpractice={malpractice_pct:.1f}%")

    return {
        "eye_contact_pct":  round(eye_contact_pct,  2),
        "malpractice_flag": malpractice_flag,
        "malpractice_pct":  round(malpractice_pct,  2),
        "no_face_pct":      round(no_face_pct,       2),
        "frames_analyzed":  analyzed,
        "face_frames":      face_frames,
        "duration_sec":     round(duration_sec,       1),
    }


# ─── Fluency Score ────────────────────────────────────────────────────────────

def compute_fluency_score(transcript: str, duration_sec: float) -> float:
    """
    Fluency based on words-per-minute.
    Ideal range: 110–160 WPM.

    FIX: If the transcript is suspiciously short relative to video duration
    (under 10 WPM), it's almost certainly a Whisper transcription failure,
    not a silent candidate. Fall back to neutral (0.5) instead of penalizing.
    A candidate who recorded 30 seconds of speech shouldn't score 0.3 fluency
    because Whisper picked up background noise instead of their voice.
    """
    if not transcript or duration_sec <= 0:
        return 0.5  # neutral — no transcript available

    words = transcript.split()
    wpm = (len(words) / duration_sec) * 60

    # ── FIX: detect likely transcription failure ──────────────────────────
    # Under 10 WPM in a video that has duration means Whisper got garbage audio.
    # Return neutral rather than punishing the candidate for a system failure.
    if wpm < 10 and duration_sec > 10:
        print(f"[score3] wpm={wpm:.0f} — likely transcription failure, using neutral fluency")
        return 0.5

    if 110 <= wpm <= 160:
        fluency = 1.0
    elif 80 <= wpm < 110 or 160 < wpm <= 185:
        fluency = 0.75
    elif 60 <= wpm < 80 or 185 < wpm <= 220:
        fluency = 0.5
    else:
        fluency = 0.3

    print(f"[score3] wpm={wpm:.0f} fluency={fluency}")
    return fluency


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def compute_score3(video_path: str, transcript: str = "") -> tuple[float, dict]:
    """
    Returns (score_out_of_100, details_dict)

    Score breakdown:
    - 60% eye contact (penalised if malpractice detected)
    - 40% speaking fluency from transcript
    """
    try:
        frame_data = analyze_frames(video_path)

        eye_score = frame_data["eye_contact_pct"]

        # Hard cap at 20 if malpractice detected
        if frame_data["malpractice_flag"]:
            eye_score = min(eye_score, 20.0)

        duration = frame_data["duration_sec"]
        fluency  = compute_fluency_score(transcript, duration) * 100 \
                   if transcript else 50.0

        score = 0.60 * eye_score + 0.40 * fluency
        print(f"[score3] eye_score={eye_score:.1f} fluency={fluency:.1f} final={score:.1f}")

        return round(score, 2), frame_data

    except Exception as e:
        print(f"[score3] ERROR: {e}")
        return 0.0, {
            "error":            str(e),
            "malpractice_flag": False,
            "eye_contact_pct":  0.0,
            "no_face_pct":      0.0,
        }