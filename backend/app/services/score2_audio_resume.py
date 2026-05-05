"""
Score 2: Compare audio transcript with resume text.
Uses Whisper for transcription, sentence-transformers for semantic comparison.
"""
import whisper
import os
from sentence_transformers import SentenceTransformer, util
from app.config import settings

_whisper_model = None
_st_model = None

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

def extract_audio_and_transcribe(video_path: str) -> dict:
    """Extract audio from video and transcribe using Whisper."""
    import moviepy.editor as mp

    audio_path = video_path.replace(".webm", ".wav").replace(".mp4", ".wav")
    if not audio_path.endswith(".wav"):
        audio_path = video_path + ".wav"

    # Extract audio
    clip = mp.VideoFileClip(video_path)
    clip.audio.write_audiofile(audio_path, verbose=False, logger=None)
    clip.close()

    # Transcribe
    model = get_whisper()
    result = model.transcribe(audio_path)
    
    # Cleanup temp audio
    if os.path.exists(audio_path):
        os.remove(audio_path)

    return {
        "text": result["text"],
        "segments": result.get("segments", [])
    }

def compute_wpm(transcript_result: dict, video_duration_sec: float) -> float:
    """Words per minute from transcript."""
    word_count = len(transcript_result["text"].split())
    if video_duration_sec > 0:
        return (word_count / video_duration_sec) * 60
    return 0

def compute_score2(video_path: str, resume_text: str) -> tuple[float, str]:
    """
    Returns (score, transcript_text)
    Score = semantic similarity between transcript and resume
    """
    try:
        result = extract_audio_and_transcribe(video_path)
        transcript = result["text"].strip()

        if not transcript:
            return 0.0, ""

        model = get_st_model()
        emb_transcript = model.encode(transcript[:2000], convert_to_tensor=True)
        emb_resume = model.encode(resume_text[:2000], convert_to_tensor=True)
        sim = float(util.cos_sim(emb_transcript, emb_resume)[0][0])
        score = max(0.0, min(1.0, sim)) * 100

        return round(score, 2), transcript
    except Exception as e:
        print(f"Score2 error: {e}")
        return 0.0, f"Error: {str(e)}"
