// ============================================================
// api.js — Drop this into your classflow-mobile folder
// Replace: <script src="data.js"> with <script src="api.js">
// Then add: <script src="api-bridge.js"> (see below)
// ============================================================

const API_URL = 'https://your-classflow-backend.onrender.com';
// Local testing: const API_URL = 'http://localhost:5000';

// ── TOKEN ──
function getToken()      { return localStorage.getItem('classflow-token'); }
function setToken(t)     { localStorage.setItem('classflow-token', t); }
function removeToken()   { localStorage.removeItem('classflow-token'); }

// ── BASE FETCH ──
async function api(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token   = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const options = { method, headers };
  if (body) options.body = JSON.stringify(body);
  try {
    const res  = await fetch(`${API_URL}${endpoint}`, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
  } catch (err) {
    console.error(`API Error [${method} ${endpoint}]:`, err.message);
    throw err;
  }
}

// ── AUTH ──
async function apiRegister(name, email, password) {
  const data = await api('/api/auth/register', 'POST', { name, email, password });
  setToken(data.token);
  return data.user;
}
async function apiLogin(email, password = '') {
  const data = await api('/api/auth/login', 'POST', { email, password });
  setToken(data.token);
  return data.user;
}
async function apiGetMe()  { return await api('/api/auth/me'); }
function  apiLogout()      { removeToken(); }

// ── SUBJECTS ──
async function apiGetSubjects()          { return await api('/api/subjects'); }
async function apiJoinSubject(code)      { return await api('/api/subjects/join', 'POST', { code }); }
async function apiCreateSubject(data)    { return await api('/api/subjects', 'POST', data); }
async function apiGetStudents(subjectId) { return await api(`/api/subjects/${subjectId}/students`); }

// ── ASSIGNMENTS ──
async function apiGetAssignments(subjectId = null) {
  const q = subjectId ? `?subject_id=${subjectId}` : '';
  return await api(`/api/assignments${q}`);
}
async function apiCreateAssignment(data) { return await api('/api/assignments', 'POST', data); }

// ── SUBMISSIONS ──

/**
 * Student hands in assignment.
 * @param {number} assignmentId
 * @param {string} fileLinks  - comma-separated file names / URLs
 * @param {string} textAnswer - typed answer (optional)
 */
async function apiSubmitAssignment(assignmentId, fileLinks, textAnswer = '') {
  return await api('/api/submissions', 'POST', {
    assignment_id: assignmentId,
    file_links:    fileLinks,
    text_answer:   textAnswer
  });
}

/** Student fetches their own submission for one assignment. */
async function apiGetMySubmission(assignmentId) {
  return await api(`/api/submissions/${assignmentId}/mine`);
}

/** Student unsubmits (recalls) their submission by submission ID. */
async function apiUnsubmit(submissionId) {
  return await api(`/api/submissions/${submissionId}/unsubmit`, 'DELETE');
}

/** Teacher gets all submissions for an assignment. */
async function apiGetSubmissions(assignmentId) {
  return await api(`/api/submissions/${assignmentId}`);
}

/**
 * Teacher grades and returns a submission.
 * @param {number} submissionId
 * @param {number} score       - 0–100
 * @param {string} feedback    - optional written feedback
 */
async function apiGradeSubmission(submissionId, score, feedback = '') {
  return await api('/api/submissions/grade', 'POST', {
    submission_id: submissionId,
    score,
    feedback
  });
}

async function apiGetGrades() { return await api('/api/grades'); }

// ── PRIVATE COMMENTS ──

/** Get private comments on a submission (student + teacher only). */
async function apiGetPrivateComments(submissionId) {
  return await api(`/api/submissions/${submissionId}/private-comments`);
}

/** Add a private comment on a submission. */
async function apiAddPrivateComment(submissionId, text) {
  return await api(`/api/submissions/${submissionId}/private-comments`, 'POST', { text });
}

// ── ANNOUNCEMENTS ──
async function apiGetAnnouncements(subjectId = null) {
  const q = subjectId ? `?subject_id=${subjectId}` : '';
  return await api(`/api/announcements${q}`);
}

/**
 * Teacher posts announcement.
 * @param {string} title
 * @param {string} body
 * @param {number|string} subjectId  - numeric ID or class name string
 * @param {string} type              - 'announcement' | 'material' | 'assignment'
 */
async function apiPostAnnouncement(title, body, subjectId, type = 'announcement') {
  return await api('/api/announcements', 'POST', { title, body, subject_id: subjectId, type });
}

/** Add a public stream comment on an announcement. */
async function apiAddStreamComment(announcementId, text) {
  return await api(`/api/announcements/${announcementId}/comments`, 'POST', { text });
}

// ── DASHBOARDS ──
async function apiStudentDashboard() { return await api('/api/dashboard/student'); }
async function apiTeacherDashboard() { return await api('/api/dashboard/teacher'); }

// ── NOTIFICATIONS ──
async function apiGetNotifications() { return await api('/api/notifications'); }
