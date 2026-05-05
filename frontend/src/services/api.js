import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.REACT_APP_API_URL || 'http://localhost:8000/api'
});

// Attach JWT token to every request if present
API.interceptors.request.use(cfg => {
  const token = localStorage.getItem('hr_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

export const hrRegister = (data) => API.post('/hr/register', data);
export const hrLogin = (data) => API.post('/hr/login', data);
export const hrMe = () => API.get('/hr/me');

export const listJobs = () => API.get('/jobs');
export const myJobs = () => API.get('/jobs/my');
export const createJob = (data) => API.post('/jobs', data);
export const getApplications = (jobId) => API.get(`/jobs/${jobId}/applications`);

export const applyJob = (formData) => API.post('/apply', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});

export const getRecordInfo = (token) => API.get(`/record/${token}`);
export const uploadVideo = (token, formData) => API.post(`/record/${token}/upload`, formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});

export default API;
