import React, { useState, useEffect } from 'react';
import { hrLogin, hrRegister, hrMe, myJobs, createJob, getApplications } from '../services/api';

const S = {
  page: { maxWidth: 960, margin: '32px auto', padding: '0 16px' },
  card: { background: 'white', borderRadius: 16, padding: 32, boxShadow: '0 4px 24px #0001', marginBottom: 24 },
  h1: { color: '#4F46E5', fontSize: 24, fontWeight: 700, marginBottom: 4 },
  label: { display: 'block', fontWeight: 600, marginBottom: 6, color: '#374151', marginTop: 14 },
  input: { width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #D1D5DB', fontSize: 15, boxSizing: 'border-box' },
  textarea: { width: '100%', padding: '10px 14px', borderRadius: 8, border: '1px solid #D1D5DB', fontSize: 14, boxSizing: 'border-box', minHeight: 90, resize: 'vertical' },
  btn: { padding: '11px 22px', borderRadius: 10, border: 'none', fontWeight: 600, fontSize: 14, cursor: 'pointer', marginTop: 16 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { background: '#F3F4F6', padding: '10px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#374151' },
  td: { padding: '10px 12px', borderBottom: '1px solid #F3F4F6', fontSize: 14 },
  badge: (q) => ({ background: q ? '#D1FAE5' : '#FEE2E2', color: q ? '#065F46' : '#991B1B', padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }),
  row: { display: 'flex', gap: 12, flexWrap: 'wrap' },
  weightRow: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 },
  error: { background: '#FEE2E2', borderRadius: 8, padding: 10, color: '#991B1B', marginTop: 10 },
  tab: (active) => ({ padding: '9px 18px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 14, background: active ? '#4F46E5' : '#F3F4F6', color: active ? 'white' : '#374151' }),
  newBadge: { display: 'inline-block', fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#EEF2FF', color: '#4F46E5', marginLeft: 6, verticalAlign: 'middle', letterSpacing: 0.3 },
  sumOk: { color: '#065F46', fontSize: 13, marginTop: 6, fontWeight: 600 },
  sumErr: { color: '#991B1B', fontSize: 13, marginTop: 6, fontWeight: 600 },
};

// ─── Auth Form ─────────────────────────────────────────────────────────────
function AuthForm({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', password: '', name: '', company: '' });
  const [error, setError] = useState('');
  const h = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async e => {
    e.preventDefault(); setError('');
    try {
      const fn = mode === 'login' ? hrLogin : hrRegister;
      const r = await fn(form);
      localStorage.setItem('hr_token', r.data.access_token);
      onLogin();
    } catch (err) { setError(err.response?.data?.detail || 'Error'); }
  };

  return (
    <div style={{ maxWidth: 440, margin: '48px auto', padding: '0 16px' }}>
      <div style={S.card}>
        <h1 style={S.h1}>HR {mode === 'login' ? 'Login' : 'Register'}</h1>
        <form onSubmit={submit}>
          {mode === 'register' && <>
            <label style={S.label}>Name</label>
            <input name="name" required value={form.name} onChange={h} style={S.input} />
            <label style={S.label}>Company</label>
            <input name="company" required value={form.company} onChange={h} style={S.input} />
          </>}
          <label style={S.label}>Email</label>
          <input name="email" type="email" required value={form.email} onChange={h} style={S.input} />
          <label style={S.label}>Password</label>
          <input name="password" type="password" required value={form.password} onChange={h} style={S.input} />
          {error && <div style={S.error}>{error}</div>}
          <button type="submit" style={{ ...S.btn, background: '#4F46E5', color: 'white', width: '100%' }}>
            {mode === 'login' ? 'Login' : 'Register'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 16, color: '#6B7280', fontSize: 13 }}>
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button style={{ background: 'none', border: 'none', color: '#4F46E5', cursor: 'pointer', fontWeight: 600 }}
            onClick={() => setMode(m => m === 'login' ? 'register' : 'login')}>
            {mode === 'login' ? 'Register' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
}

// ─── Create Job ────────────────────────────────────────────────────────────
function CreateJob({ onCreated }) {
  const [form, setForm] = useState({
    title: '',
    description: '',
    required_skills: '',
    weight_score1: 35,   // Resume vs JD
    weight_score2: 25,   // Audio vs Resume
    weight_score3: 20,   // Video Behavior
    weight_score4: 20,   // Audio vs JD
    qualifying_score: 60
  });
  const [error, setError] = useState('');
  const [ok, setOk] = useState(false);

  const h = e => setForm(f => ({
    ...f,
    [e.target.name]: e.target.type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value
  }));

  const weightSum = form.weight_score1 + form.weight_score2 + form.weight_score3 + form.weight_score4;
  const sumOk = Math.abs(weightSum - 100) <= 0.1;

  const submit = async e => {
    e.preventDefault(); setError('');
    if (!sumOk) return setError(`Weights must sum to 100 (currently ${weightSum})`);
    try {
      await createJob(form);
      setOk(true);
      onCreated();
    } catch (err) { setError(err.response?.data?.detail || 'Error'); }
  };

  if (ok) return <p style={{ color: '#065F46', fontWeight: 600 }}>✅ Job created!</p>;

  return (
    <form onSubmit={submit}>
      <label style={S.label}>Job Title *</label>
      <input name="title" required value={form.title} onChange={h} style={S.input} placeholder="e.g. Software Engineer" />

      <label style={S.label}>Job Description *</label>
      <textarea name="description" required value={form.description} onChange={h} style={S.textarea} placeholder="Full job description..." />

      <label style={S.label}>Required Skills (comma-separated) *</label>
      <input name="required_skills" required value={form.required_skills} onChange={h} style={S.input} placeholder="python, react, sql, docker" />

      <label style={S.label}>
        Scoring Weights (must sum to 100)
        <span style={{ fontWeight: 400, fontSize: 12, color: '#6B7280', marginLeft: 8 }}>
          Current total:
          <span style={{ fontWeight: 700, color: sumOk ? '#065F46' : '#DC2626', marginLeft: 4 }}>
            {weightSum}%
          </span>
        </span>
      </label>

      <div style={S.weightRow}>
        <div>
          <label style={{ fontSize: 13, color: '#6B7280', display: 'block', marginBottom: 4 }}>Resume vs JD (%)</label>
          <input name="weight_score1" type="number" min="0" max="100" step="1" value={form.weight_score1} onChange={h} style={S.input} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: '#6B7280', display: 'block', marginBottom: 4 }}>Audio vs Resume (%)</label>
          <input name="weight_score2" type="number" min="0" max="100" step="1" value={form.weight_score2} onChange={h} style={S.input} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: '#6B7280', display: 'block', marginBottom: 4 }}>
            Audio vs JD (%)
            <span style={S.newBadge}>NEW</span>
          </label>
          <input name="weight_score4" type="number" min="0" max="100" step="1" value={form.weight_score4} onChange={h} style={S.input} />
        </div>
        <div>
          <label style={{ fontSize: 13, color: '#6B7280', display: 'block', marginBottom: 4 }}>Video Behavior (%)</label>
          <input name="weight_score3" type="number" min="0" max="100" step="1" value={form.weight_score3} onChange={h} style={S.input} />
        </div>
      </div>

      {!sumOk && weightSum > 0 && (
        <p style={S.sumErr}>
          {weightSum < 100
            ? `⚠ Need ${100 - weightSum}% more to reach 100`
            : `⚠ Over by ${weightSum - 100}% — reduce one of the weights`}
        </p>
      )}
      {sumOk && (
        <p style={S.sumOk}>✓ Weights sum to 100%</p>
      )}

      <label style={S.label}>Qualifying Score (%)</label>
      <input
        name="qualifying_score"
        type="number"
        min="0"
        max="100"
        value={form.qualifying_score}
        onChange={h}
        style={{ ...S.input, maxWidth: 120 }}
      />
      <p style={{ fontSize: 12, color: '#6B7280', marginTop: 4 }}>
        Candidates scoring below this threshold will be rejected
      </p>

      {error && <div style={S.error}>{error}</div>}
      <button
        type="submit"
        style={{ ...S.btn, background: sumOk ? '#4F46E5' : '#9CA3AF', color: 'white', cursor: sumOk ? 'pointer' : 'not-allowed' }}
        disabled={!sumOk}
      >
        + Create Job
      </button>
    </form>
  );
}

// ─── Applications Table ─────────────────────────────────────────────────────
function ApplicationsTable({ jobId }) {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getApplications(jobId)
      .then(r => { setApps(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [jobId]);

  if (loading) return <p>Loading applications...</p>;
  if (!apps.length) return <p style={{ color: '#6B7280' }}>No applications yet.</p>;

  const columns = [
    'Name', 'Email',
    'S1 Resume/JD', 'S2 Audio/CV', 'S4 Audio/JD', 'S3 Video',
    'Final', 'Status', 'Malpractice', 'Eye Contact', 'Transcript'
  ];

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={S.table}>
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col} style={S.th}>
                {col}
                {col === 'S4 Audio/JD' && <span style={S.newBadge}>NEW</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {apps.map(a => (
            <tr key={a.id}>
              <td style={S.td}>{a.candidate_name}</td>
              <td style={S.td}>{a.candidate_email}</td>
              <td style={S.td}>{a.score1 != null ? `${a.score1}%` : '—'}</td>
              <td style={S.td}>{a.score2 != null ? `${a.score2}%` : '—'}</td>
              <td style={S.td}>{a.score4 != null ? `${a.score4}%` : '—'}</td>
              <td style={S.td}>{a.score3 != null ? `${a.score3}%` : '—'}</td>
              <td style={S.td}>
                {a.final_score != null
                  ? <span style={S.badge(a.is_qualified)}>{a.final_score}%</span>
                  : <span style={{ color: '#9CA3AF' }}>{a.status}</span>}
              </td>
              <td style={S.td}>
                <span style={S.badge(a.is_qualified)}>
                  {a.is_qualified
                    ? 'Qualified'
                    : a.is_qualified === false
                      ? 'Rejected'
                      : a.status}
                </span>
              </td>
              <td style={S.td}>
                {a.malpractice_flag
                  ? <span style={{ color: '#DC2626', fontWeight: 700 }}>⚠ YES</span>
                  : '—'}
              </td>
              <td style={S.td}>
                {a.eye_contact_pct != null ? `${a.eye_contact_pct}%` : '—'}
              </td>
              <td style={{
                ...S.td,
                maxWidth: 180,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: '#6B7280',
                fontSize: 12
              }}>
                {a.transcript || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Dashboard ─────────────────────────────────────────────────────────
export default function HRDashboard() {
  const [me, setMe] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [tab, setTab] = useState('jobs');
  const [selectedJob, setSelectedJob] = useState(null);

  const loadMe = () => hrMe().then(r => setMe(r.data)).catch(() => {});
  const loadJobs = () => myJobs().then(r => setJobs(r.data)).catch(() => {});

  useEffect(() => {
    if (localStorage.getItem('hr_token')) {
      loadMe();
      loadJobs();
    }
  }, []);

  if (!me) return <AuthForm onLogin={() => { loadMe(); loadJobs(); }} />;

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={S.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={S.h1}>HR Dashboard</h1>
            <p style={{ color: '#6B7280' }}>{me.name} — {me.company}</p>
          </div>
          <button
            style={{ ...S.btn, background: '#F3F4F6', color: '#374151', marginTop: 0 }}
            onClick={() => { localStorage.removeItem('hr_token'); setMe(null); }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={S.row}>
        <button style={S.tab(tab === 'jobs')} onClick={() => setTab('jobs')}>My Jobs</button>
        <button style={S.tab(tab === 'create')} onClick={() => setTab('create')}>+ New Job</button>
        {selectedJob && (
          <button style={S.tab(tab === 'apps')} onClick={() => setTab('apps')}>
            Applications — {selectedJob.title}
          </button>
        )}
      </div>

      <div style={{ marginTop: 16 }}>
        {/* My Jobs */}
        {tab === 'jobs' && (
          <div style={S.card}>
            <h2 style={{ color: '#374151', marginBottom: 16 }}>Job Postings</h2>
            {jobs.length === 0 && <p style={{ color: '#6B7280' }}>No jobs yet. Create one!</p>}
            {jobs.map(j => (
              <div key={j.id} style={{ border: '1px solid #E5E7EB', borderRadius: 10, padding: 16, marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: 0, color: '#1F2937' }}>{j.title}</h3>
                    <p style={{ color: '#6B7280', fontSize: 13, margin: '4px 0 0' }}>
                      {j.description.substring(0, 100)}...
                    </p>
                    <p style={{ color: '#9CA3AF', fontSize: 12, margin: '6px 0 0' }}>
                      Weights: Resume/JD {j.weight_score1}% | Audio/CV {j.weight_score2}% | Audio/JD {j.weight_score4 ?? '—'}% | Video {j.weight_score3}% | Qualify ≥ {j.qualifying_score}%
                    </p>
                  </div>
                  <button
                    style={{ ...S.btn, background: '#EEF2FF', color: '#4F46E5', marginTop: 0, fontSize: 13 }}
                    onClick={() => { setSelectedJob(j); setTab('apps'); }}
                  >
                    View Applications →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Job */}
        {tab === 'create' && (
          <div style={S.card}>
            <h2 style={{ color: '#374151', marginBottom: 4 }}>Create New Job Posting</h2>
            <p style={{ color: '#6B7280', fontSize: 13, marginBottom: 16 }}>
              4 scores are computed per candidate — set how much each contributes to the final score.
            </p>
            <CreateJob onCreated={() => { loadJobs(); setTab('jobs'); }} />
          </div>
        )}

        {/* Applications */}
        {tab === 'apps' && selectedJob && (
          <div style={S.card}>
            <h2 style={{ color: '#374151', marginBottom: 4 }}>Applications — {selectedJob.title}</h2>
            <p style={{ color: '#6B7280', marginBottom: 8, fontSize: 13 }}>
              Qualifying score: {selectedJob.qualifying_score}% | Sorted by final score
            </p>
            <div style={{ display: 'flex', gap: 24, marginBottom: 16, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                <b style={{ color: '#374151' }}>S1</b> Resume vs JD ({selectedJob.weight_score1}%)
              </span>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                <b style={{ color: '#374151' }}>S2</b> Audio vs Resume ({selectedJob.weight_score2}%)
              </span>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                <b style={{ color: '#4F46E5' }}>S4</b> Audio vs JD ({selectedJob.weight_score4 ?? '—'}%)
                <span style={S.newBadge}>NEW</span>
              </span>
              <span style={{ fontSize: 12, color: '#6B7280' }}>
                <b style={{ color: '#374151' }}>S3</b> Video Behavior ({selectedJob.weight_score3}%)
              </span>
            </div>
            <ApplicationsTable jobId={selectedJob.id} />
          </div>
        )}
      </div>
    </div>
  );
}
