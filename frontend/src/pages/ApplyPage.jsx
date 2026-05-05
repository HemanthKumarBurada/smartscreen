import React, { useState, useEffect } from 'react';
import { listJobs, applyJob } from '../services/api';

const S = {
  page: { maxWidth: 600, margin: '48px auto', padding: '0 16px' },
  card: { background: 'white', borderRadius: 16, padding: 36, boxShadow: '0 4px 24px #0001' },
  h1: { color: '#4F46E5', fontSize: 28, fontWeight: 700, marginBottom: 8 },
  sub: { color: '#6B7280', marginBottom: 28 },
  label: { display: 'block', fontWeight: 600, marginBottom: 6, color: '#374151' },
  input: { width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #D1D5DB', fontSize: 15, boxSizing: 'border-box', marginBottom: 18 },
  select: { width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #D1D5DB', fontSize: 15, boxSizing: 'border-box', marginBottom: 18, background: 'white' },
  btn: { width: '100%', padding: '13px', background: '#4F46E5', color: 'white', border: 'none', borderRadius: 10, fontSize: 16, fontWeight: 600, cursor: 'pointer' },
  success: { background: '#D1FAE5', borderRadius: 10, padding: 20, color: '#065F46', textAlign: 'center', marginTop: 20 },
  error: { background: '#FEE2E2', borderRadius: 10, padding: 12, color: '#991B1B', marginTop: 12 },
};

export default function ApplyPage() {
  const [jobs, setJobs] = useState([]);
  const [form, setForm] = useState({ job_id: '', name: '', email: '', resume: null });
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const r = await listJobs();
        console.log("API response:", r.data); // 🔍 debug

        // ✅ SAFE handling for both formats
        const jobData = Array.isArray(r.data)
          ? r.data
          : r.data.jobs || [];

        setJobs(jobData);
      } catch (err) {
  console.error("Fetch jobs failed:", err);
  setError('Could not load jobs. Please refresh the page.');
}
    };

    fetchJobs();
  }, []);

  const handle = e => {
    const { name, value, files } = e.target;
    setForm(f => ({ ...f, [name]: files ? files[0] : value }));
  };

  const submit = async e => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const fd = new FormData();
      fd.append('job_id', form.job_id);
      fd.append('name', form.name);
      fd.append('email', form.email);
      fd.append('resume', form.resume);

      await applyJob(fd);
      setDone(true);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Submission failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (done) return (
    <div style={S.page}>
      <div style={S.card}>
        <div style={S.success}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📬</div>
          <h2>Application Submitted!</h2>
          <p>Check your email for a <strong>live video recording link</strong>.</p>
          <p style={{ fontSize: 13, color: '#6B7280' }}>The link is valid for 48 hours.</p>
        </div>
      </div>
    </div>
  );

  return (
    <div style={S.page}>
      <div style={S.card}>
        <h1 style={S.h1}>Apply for a Position</h1>
        <p style={S.sub}>Submit your resume. You'll receive an email with a live video recording link.</p>

        <form onSubmit={submit}>
          <label style={S.label}>Job Position *</label>
          <select
            name="job_id"
            required
            value={form.job_id}
            onChange={handle}
            style={S.select}
          >
            <option value="">Select a position...</option>

            {/* ✅ SAFE MAP */}
            {Array.isArray(jobs) && jobs.map(j => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </select>

          <label style={S.label}>Full Name *</label>
          <input
            name="name"
            required
            placeholder="Your full name"
            value={form.name}
            onChange={handle}
            style={S.input}
          />

          <label style={S.label}>Email Address *</label>
          <input
            name="email"
            type="email"
            required
            placeholder="your@email.com"
            value={form.email}
            onChange={handle}
            style={S.input}
          />

          <label style={S.label}>Resume (PDF or DOCX) *</label>
          <input
            name="resume"
            type="file"
            accept=".pdf,.docx,.doc"
            required
            onChange={handle}
            style={S.input}
          />

          {error && <div style={S.error}>{error}</div>}

          <button type="submit" style={S.btn} disabled={loading}>
            {loading ? 'Submitting...' : '📤 Submit Application'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: 20, color: '#6B7280', fontSize: 13 }}>
          Are you an HR? <a href="/hr" style={{ color: '#4F46E5' }}>Login here</a>
        </p>
      </div>
    </div>
  );
}