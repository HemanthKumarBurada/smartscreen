import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import ApplyPage from './pages/ApplyPage';
import RecordPage from './pages/RecordPage';
import HRDashboard from './pages/HRDashboard';

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#F8F7FF', fontFamily: 'Segoe UI, Arial, sans-serif' }}>
        <nav style={{ background: '#4F46E5', padding: '14px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Link to="/" style={{ color: 'white', textDecoration: 'none', fontSize: 20, fontWeight: 700 }}>
            🎯 SmartScreen
          </Link>
          <div style={{ display: 'flex', gap: 20 }}>
            <Link to="/" style={{ color: '#C7D2FE', textDecoration: 'none' }}>Apply</Link>
            <Link to="/hr" style={{ color: '#C7D2FE', textDecoration: 'none' }}>HR Login</Link>
          </div>
        </nav>
        <Routes>
          <Route path="/" element={<ApplyPage />} />
          <Route path="/record/:token" element={<RecordPage />} />
          <Route path="/hr" element={<HRDashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
