"""
Score 3: Video frame behavioral analysis.
- Eye contact % (face centered in frame)
- Malpractice detection (multiple faces = flag)
- Communication fluency from transcript
"""
import cv2
import numpy as np
import os

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def analyze_frames(video_path: str) -> dict:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps

    sample_interval = int(fps)  # 1 frame per second
    frame_idx = 0
    analyzed = 0
    eye_contact_frames = 0
    malpractice_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            analyzed += 1

            if len(faces) == 1:
                # Eye contact: check if face is roughly centered horizontally
                h, w = frame.shape[:2]
                (x, y, fw, fh) = faces[0]
                face_cx = x + fw // 2
                frame_cx = w // 2
                offset = abs(face_cx - frame_cx) / (w / 2)  # 0=center, 1=edge
                if offset < 0.35:  # within 35% of center
                    eye_contact_frames += 1
            elif len(faces) > 1:
                malpractice_frames += 1

        frame_idx += 1

    cap.release()

    eye_contact_pct = (eye_contact_frames / analyzed * 100) if analyzed > 0 else 0
    malpractice_pct = (malpractice_frames / analyzed * 100) if analyzed > 0 else 0
    malpractice_flag = malpractice_pct > 10  # >10% frames with multiple faces = flagged

    return {
        "eye_contact_pct": round(eye_contact_pct, 2),
        "malpractice_flag": malpractice_flag,
        "malpractice_pct": round(malpractice_pct, 2),
        "frames_analyzed": analyzed,
        "duration_sec": round(duration_sec, 1)
    }

def compute_fluency_score(transcript: str, duration_sec: float) -> float:
    """Simple fluency: WPM + sentence variety."""
    words = transcript.split()
    wpm = (len(words) / duration_sec * 60) if duration_sec > 0 else 0
    # Ideal range: 100–160 WPM
    if 100 <= wpm <= 160:
        fluency = 1.0
    elif wpm < 60 or wpm > 220:
        fluency = 0.4
    else:
        fluency = 0.7
    return fluency

def compute_score3(video_path: str, transcript: str = "") -> tuple[float, dict]:
    """
    Returns (score_out_of_100, details_dict)
    """
    try:
        frame_data = analyze_frames(video_path)
        
        # Eye contact score (0–100)
        eye_score = frame_data["eye_contact_pct"]
        
        # Malpractice penalty
        if frame_data["malpractice_flag"]:
            eye_score = min(eye_score, 20.0)  # hard cap at 20 if malpractice
        
        # Fluency score
        duration = frame_data["duration_sec"]
        fluency = compute_fluency_score(transcript, duration) * 100 if transcript else 50.0

        # Final score3 = 60% eye contact + 40% fluency
        score = 0.60 * eye_score + 0.40 * fluency

        return round(score, 2), frame_data
    except Exception as e:
        print(f"Score3 error: {e}")
        return 0.0, {"error": str(e), "malpractice_flag": False, "eye_contact_pct": 0}
