import React, { useRef, useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const MAX_SECONDS = 150; // 2 minutes 30 seconds

// ─── Codec Selection ──────────────────────────────────────────────────────────
// Explicitly request 'opus' audio codec so FFmpeg/moviepy can cleanly extract
// audio on Windows. Without this, Chrome may pick a codec Whisper struggles with.
function getBestMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm;codecs=opus',
    'video/webm',
  ];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return ''; // browser default fallback
}

export default function RecordPage() {
  const { token } = useParams();
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  const [stage, setStage] = useState('idle');
  const [previewUrl, setPreviewUrl] = useState(null);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [error, setError] = useState('');
  const [jobInfo, setJobInfo] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(MAX_SECONDS);
  const [rerecordUsed, setRerecordUsed] = useState(false);
  const [mimeType, setMimeType] = useState('');

  useEffect(() => {
    // Detect best codec on mount so we can show a warning early if needed
    setMimeType(getBestMimeType());
  }, []);

  useEffect(() => {
    axios.get(`/api/record/${token}`)
      .then(r => setJobInfo(r.data))
      .catch(() => setError('Invalid or expired link.'));
  }, [token]);

  useEffect(() => {
    if (previewUrl && videoRef.current) {
      videoRef.current.src = previewUrl;
    }
  }, [previewUrl]);

  // Countdown timer during recording
  useEffect(() => {
    if (stage === 'recording') {
      setSecondsLeft(MAX_SECONDS);
      timerRef.current = setInterval(() => {
        setSecondsLeft(prev => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            stopRecording();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [stage]);

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const timerColor = secondsLeft <= 30 ? '#e74c3c' : secondsLeft <= 60 ? '#e67e22' : '#27ae60';

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        // ── FIX: explicit audio constraints ───────────────────────────────
        // echoCancellation + noiseSuppression reduces background noise pickup.
        // sampleRate 16000 matches Whisper's native training rate → better transcription.
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.muted = true;
        videoRef.current.play();
      }
      setStage('ready');
    } catch {
      setError('Camera/microphone access denied. Please allow permissions and refresh.');
    }
  };

  const startRecording = () => {
    chunksRef.current = [];

    // ── FIX: pass explicit mimeType with opus audio codec ─────────────────
    // Without specifying the codec, Chrome on Windows often records audio in
    // a format that moviepy/FFmpeg cannot cleanly decode, causing Whisper to
    // receive garbage audio or silence.
    const options = mimeType ? { mimeType } : {};
    const mr = new MediaRecorder(streamRef.current, options);
    mediaRecorderRef.current = mr;

    mr.ondataavailable = e => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mr.onstop = () => {
      // Use the actual recorded mimeType for the Blob (may differ from requested)
      const actualType = mr.mimeType || 'video/webm';
      const blob = new Blob(chunksRef.current, { type: actualType });
      const url = URL.createObjectURL(blob);
      setRecordedBlob(blob);
      setPreviewUrl(url);
      setStage('preview');
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
    };

    mr.start();
    setStage('recording');
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  const handleRerecord = () => {
    setRerecordUsed(true);
    setPreviewUrl(null);
    setRecordedBlob(null);
    setSecondsLeft(MAX_SECONDS);
    startCamera();
  };

  const submitVideo = async () => {
    if (!recordedBlob) return;
    setStage('uploading');
    try {
      const formData = new FormData();
      // Always send as recording.webm — backend already handles this extension
      formData.append('video', recordedBlob, 'recording.webm');
      await axios.post(`/api/record/${token}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setStage('done');
    } catch {
      setError('Upload failed. Please try again.');
      setStage('preview');
    }
  };

  if (error) return (
    <div style={S.center}>
      <div style={S.card}><h2 style={{ color: '#e74c3c' }}>⚠️ {error}</h2></div>
    </div>
  );

  if (!jobInfo) return <div style={S.center}><p>Loading...</p></div>;

  return (
    <div style={S.center}>
      <div style={S.card}>
        <h2 style={{ marginBottom: 4 }}>🎥 Video Interview</h2>
        <p style={{ color: '#666', marginBottom: 16 }}>
          Position: <strong>{jobInfo.job_title}</strong>
        </p>

        {stage === 'done' ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 60 }}>✅</div>
            <h3>Video Submitted!</h3>
            <p>You will receive your result by email within a few minutes.</p>
          </div>
        ) : (
          <>
            {stage === 'recording' && (
              <div style={{ textAlign: 'center', marginBottom: 12 }}>
                <div style={{
                  fontSize: 42, fontWeight: 700, color: timerColor,
                  fontFamily: 'monospace', letterSpacing: 2
                }}>
                  {formatTime(secondsLeft)}
                </div>
                <div style={{ fontSize: 13, color: '#888' }}>
                  {secondsLeft <= 30 ? '⚠️ Almost out of time!' : 'Time remaining'}
                </div>
                <div style={{ height: 6, background: '#eee', borderRadius: 4, marginTop: 8 }}>
                  <div style={{
                    height: '100%', borderRadius: 4,
                    background: timerColor,
                    width: `${(secondsLeft / MAX_SECONDS) * 100}%`,
                    transition: 'width 1s linear, background 0.5s'
                  }} />
                </div>
              </div>
            )}

            <video
              ref={videoRef}
              autoPlay={stage === 'ready' || stage === 'recording'}
              controls={stage === 'preview'}
              muted={stage !== 'preview'}
              style={S.video}
            />

            <div style={{ marginTop: 16, display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              {stage === 'idle' && (
                <button style={S.btn} onClick={startCamera}>📷 Enable Camera</button>
              )}
              {stage === 'ready' && (
                <button style={{ ...S.btn, background: '#e74c3c' }} onClick={startRecording}>
                  ⏺ Start Recording
                </button>
              )}
              {stage === 'recording' && (
                <button style={{ ...S.btn, background: '#e67e22' }} onClick={stopRecording}>
                  ⏹ Stop Recording
                </button>
              )}
              {stage === 'preview' && (
                <>
                  {!rerecordUsed && (
                    <button style={{ ...S.btn, background: '#7f8c8d' }} onClick={handleRerecord}>
                      🔄 Re-record (1 time only)
                    </button>
                  )}
                  <button style={{ ...S.btn, background: '#27ae60' }} onClick={submitVideo}>
                    🚀 Submit Video
                  </button>
                </>
              )}
              {stage === 'uploading' && (
                <button style={{ ...S.btn, background: '#95a5a6' }} disabled>
                  ⏳ Uploading...
                </button>
              )}
            </div>

            {stage === 'idle' && (
              <div style={S.tips}>
                <p><strong>📋 Tips before you start:</strong></p>
                <ul style={{ paddingLeft: 20, color: '#555', lineHeight: 1.8 }}>
                  <li>Find a well-lit, quiet place</li>
                  <li>Speak clearly about your experience</li>
                  <li>Keep your face visible in frame</li>
                  <li>⏱️ Max recording time: <strong>2 minutes 30 seconds</strong></li>
                  <li>You get <strong>1 chance to re-record</strong> if needed</li>
                </ul>
              </div>
            )}

            {stage === 'preview' && rerecordUsed && (
              <div style={{ marginTop: 12, background: '#FEF3C7', borderRadius: 8, padding: 10, fontSize: 13, color: '#92400E', textAlign: 'center' }}>
                ⚠️ You have already used your re-record. Please submit this video.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

const S = {
  center: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f6fa', padding: 16 },
  card: { background: '#fff', borderRadius: 12, padding: 32, maxWidth: 640, width: '100%', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' },
  video: { width: '100%', borderRadius: 8, background: '#000', minHeight: 300 },
  btn: { padding: '10px 24px', background: '#3498db', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15, fontWeight: 600 },
  tips: { marginTop: 20, background: '#f8f9fa', borderRadius: 8, padding: 16 }
};
