/**
 * api-bridge.js — Connects ClassFlow frontend to the real backend.
 *
 * HOW TO USE:
 * 1. Add api.js and api-bridge.js to your classflow-mobile folder
 * 2. In index.html, replace:
 *      <script src="data.js"></script>
 *    With:
 *      <script src="api.js"></script>
 *      <script src="api-bridge.js"></script>
 * 3. Keep script.js and submission.js — they still handle the UI.
 *    This file overrides the data-fetching parts only.
 */

// ─────────────────────────────────────────
// OVERRIDE: doLogin — use real API
// ─────────────────────────────────────────
window.doLogin = async function () {
  const email = document.getElementById('email-input').value.trim();
  if (!email || !email.includes('@')) {
    alert('Please enter a valid college email');
    return;
  }

  try {
    // Demo: no password required in dev mode
    currentUser = await apiLogin(email, '');

    document.getElementById('login-screen').classList.remove('active');

    if (currentUser.role === 'teacher') {
      document.getElementById('teacher-app').classList.add('active');
      document.getElementById('t-user-name').textContent  = currentUser.name;
      document.getElementById('t-user-email').textContent = currentUser.email;
      await renderTeacherDashboardFromAPI();
    } else {
      document.getElementById('student-app').classList.add('active');
      document.getElementById('s-user-name').textContent  = currentUser.name;
      document.getElementById('s-user-email').textContent = currentUser.email;
      const firstName = currentUser.name.split(' ')[0];
      document.getElementById('s-greeting').textContent = 'Good morning, ' + firstName + ' 👋';
      await renderStudentDashboardFromAPI();
    }
  } catch (err) {
    alert('Login failed: ' + err.message);
  }
};

// ─────────────────────────────────────────
// STUDENT DASHBOARD — from API
// ─────────────────────────────────────────
async function renderStudentDashboardFromAPI() {
  try {
    const [dash, subjects, assignments, notifications] = await Promise.all([
      apiStudentDashboard(),
      apiGetSubjects(),
      apiGetAssignments(),
      apiGetNotifications()
    ]);

    // Populate global arrays so existing render functions still work
    window.SUBJECTS      = subjects;
    window.ASSIGNMENTS   = assignments;
    window.NOTIFICATIONS = notifications;

    // Metrics
    const dueEl = document.getElementById('s-due-count');
    const avgEl = document.getElementById('s-avg-grade');
    if (dueEl) dueEl.textContent = dash.due_this_week || 0;
    if (avgEl) avgEl.textContent = (dash.avg_grade || '--') + '%';

    // Due soon list
    const dueSoonEl = document.getElementById('due-soon-list');
    if (dueSoonEl && dash.due_soon) {
      dueSoonEl.innerHTML = dash.due_soon.map(a => {
        const sub = subjects.find(s => s.id === a.subject) || {};
        const bc  = a.due.includes('Today') ? 'badge-red' : 'badge-amber';
        return `<div class="row" onclick="openAssignment(${a.id})">
          <div class="dot" style="background:${sub.color||'#888'}"></div>
          <div style="flex:1"><p style="font-size:13px;font-weight:500;margin:0">${a.title}</p>
          <p style="font-size:11px;color:#888;margin:2px 0 0">${sub.name||''}</p></div>
          <span class="badge ${bc}">${a.due}</span></div>`;
      }).join('');
    }

    // Recently graded list
    const gradedEl = document.getElementById('graded-list');
    if (gradedEl && dash.recently_graded) {
      gradedEl.innerHTML = dash.recently_graded.map(a => {
        const sub = subjects.find(s => s.id === a.subject) || {};
        const bc  = a.score >= 80 ? 'badge-green' : a.score >= 60 ? 'badge-amber' : 'badge-red';
        return `<div class="row" onclick="showStudentPage('s-grades', null)">
          <div class="dot" style="background:${sub.color||'#888'}"></div>
          <div style="flex:1"><p style="font-size:13px;margin:0">${a.title}</p>
          <p style="font-size:11px;color:#888;margin:2px 0 0">${sub.name||''}</p></div>
          <span class="badge ${bc}">${a.score}/100</span></div>`;
      }).join('');
    }

    // Re-render existing UI sections using now-populated globals
    renderClassGrid();
    renderAssignmentList();
    renderGrades();
    renderNotifications();

  } catch (err) {
    console.error('Dashboard load failed:', err);
  }
}

// ─────────────────────────────────────────
// TEACHER DASHBOARD — from API
// ─────────────────────────────────────────
async function renderTeacherDashboardFromAPI() {
  try {
    const [dash, subjects, assignments] = await Promise.all([
      apiTeacherDashboard(),
      apiGetSubjects(),
      apiGetAssignments()
    ]);

    window.SUBJECTS    = subjects;
    window.ASSIGNMENTS = assignments;

    // Metrics
    const fields = [
      ['total_students',  '.metric-card:nth-child(1) .mvalue'],
      ['pending_grading', '.metric-card:nth-child(2) .mvalue'],
      ['submission_rate', '.metric-card:nth-child(3) .mvalue'],
    ];
    const grid = document.querySelector('#t-dashboard .metrics-grid');
    if (grid) {
      const cards = grid.querySelectorAll('.metric-card .mvalue');
      if (cards[0]) cards[0].textContent = dash.total_students    || 0;
      if (cards[1]) cards[1].textContent = dash.pending_grading   || 0;
      if (cards[2]) cards[2].textContent = (dash.submission_rate  || 0) + '%';
    }

    // Needs grading list
    const queueEl = document.getElementById('grade-queue');
    if (queueEl && dash.needs_grading) {
      queueEl.innerHTML = dash.needs_grading.map(s => `
        <div class="sub-list-item" onclick="openTeacherGradePanel(${s.student_id}, ${s.assignment_id})">
          <div class="avatar" style="background:#dceeff;color:#1a5a9a;">${s.initials||'??'}</div>
          <div style="flex:1;">
            <p style="font-size:13px;font-weight:500;margin:0;">${s.student_name} — ${assignments.find(a=>a.id===s.assignment_id)?.title||'Assignment'}</p>
            <p style="font-size:11px;color:#888;margin:2px 0 0;">Submitted ${s.submitted_at}</p>
          </div>
          <span class="badge badge-amber">Grade →</span>
        </div>`).join('');
    }

    renderAnnouncementList();

  } catch (err) {
    console.error('Teacher dashboard load failed:', err);
  }
}

// ─────────────────────────────────────────
// OVERRIDE: renderStudentDashboard (called by script.js internally)
// ─────────────────────────────────────────
window.renderStudentDashboard = function () {
  renderStudentDashboardFromAPI();
};

window.renderTeacherDashboard = function () {
  renderTeacherDashboardFromAPI();
};

// ─────────────────────────────────────────
// OVERRIDE: finalSubmit — use real API
// Matches finalSubmit() in submission.js
// ─────────────────────────────────────────
window.finalSubmit = async function (id) {
  closeSubmitConfirm();
  const st = SUBMISSION_STATE[id];

  try {
    // Combine file names and links into one comma-separated string
    const allLinks = [
      ...st.files.map(f => f.name),
      ...st.links
    ].join(',');

    const result = await apiSubmitAssignment(id, allLinks, st.text || '');

    // Store backend submission ID so we can unsubmit or comment later
    st.backendId   = result.submission.id;
    st.status      = 'submitted';
    st.submittedAt = result.submission.submitted_at;

    // Update local ASSIGNMENTS array so UI reflects change
    const a = ASSIGNMENTS.find(x => x.id === id);
    if (a) a.status = 'submitted';

    NOTIFICATIONS.unshift({
      type: 'success', icon: '✅',
      title: `${a ? a.title : 'Assignment'} submitted`,
      body: 'Your assignment was handed in successfully.',
      time: 'Just now'
    });

    const sub = SUBJECTS.find(s => s.id === (a ? a.subject : null));
    renderAssignDetailPage(a, sub, st);
    renderStudentDashboard();
    showToast('✅ Assignment submitted!');

  } catch (err) {
    showToast('Submission failed: ' + err.message, '#E24B4A');
  }
};

// ─────────────────────────────────────────
// OVERRIDE: unsubmitAssignment — use real API
// ─────────────────────────────────────────
window.unsubmitAssignment = async function (id) {
  const st = SUBMISSION_STATE[id];
  if (!st || !st.backendId) {
    showToast('Cannot unsubmit — submission ID not found', '#E24B4A');
    return;
  }
  try {
    await apiUnsubmit(st.backendId);
    st.status      = 'pending';
    st.submittedAt = null;
    st.backendId   = null;
    const a   = ASSIGNMENTS.find(x => x.id === id);
    if (a) a.status = 'pending';
    const sub = SUBJECTS.find(s => s.id === (a ? a.subject : null));
    renderAssignDetailPage(a, sub, st);
    renderStudentDashboard();
    showToast('Submission recalled. You can edit and resubmit.', '#7a4800');
  } catch (err) {
    showToast('Unsubmit failed: ' + err.message, '#E24B4A');
  }
};

// ─────────────────────────────────────────
// OVERRIDE: returnGradeToStudent — use real API
// ─────────────────────────────────────────
window.returnGradeToStudent = async function (key, studentId, assignId) {
  const score    = TEACHER_GRADES[key] ? TEACHER_GRADES[key].score : null;
  const feedback = (document.getElementById('grade-feedback-' + key) || {}).value || '';
  if (!score && score !== 0) { showToast('Please enter a grade first', '#E24B4A'); return; }

  // We need the backend submission ID — fetch it first
  try {
    const subData = await apiGetSubmissions(assignId);
    const sub     = subData.submissions.find(s => s.student_id === studentId);
    if (!sub) { showToast('Submission not found in database', '#E24B4A'); return; }

    await apiGradeSubmission(sub.id, score, feedback);

    // Update local state
    GRADED_IDS.add(studentId);
    ensureSubState(assignId);
    SUBMISSION_STATE[assignId].status   = 'graded';
    SUBMISSION_STATE[assignId].score    = score;
    SUBMISSION_STATE[assignId].feedback = feedback || 'Good work!';

    const a       = ASSIGNMENTS.find(x => x.id === assignId);
    if (a) { a.status = 'graded'; a.score = score; }

    const student = { name: sub.student_name };
    NOTIFICATIONS.unshift({
      type: 'success', icon: '🎯',
      title: `${a ? a.title : 'Assignment'} graded — ${score}/100`,
      body:  `${student.name}: ${getLetterGrade(score).letter}`,
      time:  'Just now'
    });

    document.getElementById('teacher-grade-panel').style.display = 'none';
    showToast(`✅ Grade returned to ${student.name}!`);
    renderGradeQueue();

  } catch (err) {
    showToast('Grading failed: ' + err.message, '#E24B4A');
  }
};

// ─────────────────────────────────────────
// OVERRIDE: postAnnouncement — use real API
// ─────────────────────────────────────────
window.postAnnouncement = async function () {
  const title = document.getElementById('ann-title').value.trim();
  const body  = document.getElementById('ann-body').value.trim();
  const cls   = document.getElementById('ann-class').value;
  if (!title || !body) { alert('Please fill in both title and message'); return; }

  try {
    // Send class name — backend resolves it to subject_id
    const ann = await apiPostAnnouncement(title, body, cls === 'All classes' ? null : cls);

    // Push into local ANNOUNCEMENTS for immediate UI update
    ANNOUNCEMENTS.unshift({
      title:  ann.title,
      body:   ann.body,
      class:  cls,
      time:   'Just now',
      author: currentUser ? currentUser.name : 'Teacher'
    });

    NOTIFICATIONS.unshift({
      type: 'warning', icon: '📢',
      title: title,
      body:  body + ' — ' + cls,
      time:  'Just now'
    });

    document.getElementById('ann-title').value = '';
    document.getElementById('ann-body').value  = '';

    renderAnnouncementList();
    if (currentTeacherClassId) renderTeacherClassStream(currentTeacherClassId);
    if (currentClassId)        renderClassStream(currentClassId);

    showToast('✅ Announcement posted!');

  } catch (err) {
    alert('Failed to post announcement: ' + err.message);
  }
};

// ─────────────────────────────────────────
// OVERRIDE: addClassComment — use real API
// ─────────────────────────────────────────
window.addClassComment = async function (postId) {
  const input = document.getElementById('comment-' + postId);
  const text  = input ? input.value.trim() : '';
  if (!text) return;

  try {
    const comment = await apiAddStreamComment(postId, text);
    if (!STREAM_COMMENTS[postId]) STREAM_COMMENTS[postId] = [];
    STREAM_COMMENTS[postId].push(comment);
    renderClassStream(currentClassId);
  } catch (err) {
    showToast('Comment failed: ' + err.message, '#E24B4A');
  }
};

// ─────────────────────────────────────────
// OVERRIDE: addPrivateComment — use real API
// ─────────────────────────────────────────
window.addPrivateComment = async function (id) {
  const input = document.getElementById('private-comment-input');
  const text  = input ? input.value.trim() : '';
  if (!text) return;
  const st = SUBMISSION_STATE[id];
  if (!st || !st.backendId) {
    // Fallback to in-memory if not yet submitted to backend
    const ini = currentUser ? currentUser.name.split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase() : 'PS';
    st.privateComments.push({ author: currentUser ? currentUser.name : 'Priya Sharma', initials: ini, text, time: 'Just now', role: 'student' });
    const list = document.getElementById('private-comments-list');
    if (list) list.innerHTML = renderPrivateComments(st);
    if (input) input.value = '';
    return;
  }
  try {
    const comment = await apiAddPrivateComment(st.backendId, text);
    st.privateComments.push(comment);
    const list = document.getElementById('private-comments-list');
    if (list) list.innerHTML = renderPrivateComments(st);
    if (input) input.value = '';
  } catch (err) {
    showToast('Comment failed: ' + err.message, '#E24B4A');
  }
};

// ─────────────────────────────────────────
// AUTO RESTORE SESSION on page load
// ─────────────────────────────────────────
(async function restoreSession() {
  const token = getToken();
  if (!token) return;
  try {
    currentUser = await apiGetMe();
    document.getElementById('login-screen').classList.remove('active');
    if (currentUser.role === 'teacher') {
      document.getElementById('teacher-app').classList.add('active');
      document.getElementById('t-user-name').textContent  = currentUser.name;
      document.getElementById('t-user-email').textContent = currentUser.email;
      await renderTeacherDashboardFromAPI();
    } else {
      document.getElementById('student-app').classList.add('active');
      document.getElementById('s-user-name').textContent  = currentUser.name;
      document.getElementById('s-user-email').textContent = currentUser.email;
      const firstName = currentUser.name.split(' ')[0];
      const greetEl   = document.getElementById('s-greeting');
      if (greetEl) greetEl.textContent = 'Good morning, ' + firstName + ' 👋';
      await renderStudentDashboardFromAPI();
    }
  } catch (err) {
    // Token expired or invalid — stay on login screen
    removeToken();
  }
})();
