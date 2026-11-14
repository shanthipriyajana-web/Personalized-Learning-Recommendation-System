/**
 * Learner Dashboard Interactive Client
 * Communicates exclusively with REST API endpoints.
 */

let activeQuizAttemptId = null;
let activeAssessmentId = null;
let activeQuestions = [];

document.addEventListener('DOMContentLoaded', () => {
  loadRecommendations();
  loadMasteryData();
  loadLearningPath();
  loadCourseCatalog();
  loadAssessmentHistory();
  loadSupportTickets();

  // Support ticket form submission
  const supportForm = document.getElementById('support-ticket-form');
  if (supportForm) {
    supportForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const category = document.getElementById('ticket-category').value;
      const subject = document.getElementById('ticket-subject').value.trim();
      const description = document.getElementById('ticket-description').value.trim();

      try {
        await apiFetch('/api/support/tickets', {
          method: 'POST',
          body: JSON.stringify({ category, subject, description })
        });
        showToast('Support ticket submitted successfully.', 'success');
        closeModal('support-modal');
        supportForm.reset();
        loadSupportTickets();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }
});

// -------------------------------------------------------------------------
// 1. RECOMMENDATIONS
// -------------------------------------------------------------------------
async function loadRecommendations() {
  const container = document.getElementById('recommendations-container');
  try {
    const recs = await apiFetch('/api/recommendations/me');
    if (!recs || recs.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 40px;">
          <p style="color: var(--gray-600); margin-bottom: 16px;">No active recommendations found. Click below to generate your initial plan.</p>
          <button onclick="triggerRecommendationGeneration()" class="btn btn-primary btn-sm">Generate Recommendations</button>
        </div>
      `;
      return;
    }

    let html = '';
    recs.forEach(rec => {
      const reasonClass = `rec-reason-${rec.reason_code}`;
      html += `
        <div class="rec-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
            <div>
              <span class="rec-badge ${reasonClass}">${rec.reason_code.replace(/_/g, ' ')}</span>
              <h4 style="font-size: 1.15rem; font-weight: 700; color: var(--gray-900); margin: 4px 0;">
                ${rec.title}
              </h4>
              <p style="font-size: 0.85rem; color: var(--gray-500);">
                Course: <strong>${rec.course_title}</strong> (${rec.course_code}) | Difficulty: <strong>${rec.difficulty}</strong> | Est. Time: ${rec.estimated_minutes} mins
              </p>
            </div>
            <span style="font-size: 0.85rem; font-weight: 700; color: var(--primary); background: var(--primary-light); padding: 4px 10px; border-radius: var(--radius-sm);">
              Score: ${rec.score}
            </span>
          </div>

          <div class="rec-explanation">
            <strong>Why Recommended:</strong> ${rec.explanation}
          </div>

          <div style="display: flex; gap: 10px; align-items: center;">
            <button onclick="showToast('Activity started: ${rec.title}', 'info')" class="btn btn-primary btn-sm">
              ▶ Start Activity
            </button>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Failed to load recommendations: ${err.message}</div>`;
  }
}

async function triggerRecommendationGeneration() {
  try {
    showToast('Recalculating personalized recommendations...', 'info');
    await apiFetch('/api/recommendations/generate', { method: 'POST' });
    showToast('Fresh recommendations generated!', 'success');
    loadRecommendations();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// -------------------------------------------------------------------------
// 2. SKILL MASTERY
// -------------------------------------------------------------------------
async function loadMasteryData() {
  const container = document.getElementById('mastery-container');
  try {
    const masteries = await apiFetch('/api/learners/me/mastery');
    let masteredCount = 0;

    if (!masteries || masteries.length === 0) {
      container.innerHTML = `<div class="card" style="grid-column: 1/-1;">No assessment attempts recorded yet. Take an assessment to evaluate your skill masteries.</div>`;
      document.getElementById('stat-mastered-count').innerText = '0';
      return;
    }

    let html = '';
    masteries.forEach(m => {
      if (m.mastery_percentage >= 70.0) masteredCount++;

      let barClass = 'mastery-needs-improvement';
      if (m.mastery_level === 'DEVELOPING') barClass = 'mastery-developing';
      else if (m.mastery_level === 'PROFICIENT') barClass = 'mastery-proficient';
      else if (m.mastery_level === 'MASTERED') barClass = 'mastery-mastered';

      html += `
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: var(--gray-900); font-size: 0.95rem;">${m.skill_name}</strong>
            <span style="font-size: 0.85rem; font-weight: 700; color: var(--gray-700);">${m.mastery_percentage}%</span>
          </div>

          <div class="mastery-bar-container">
            <div class="mastery-bar-fill ${barClass}" style="width: ${m.mastery_percentage}%;"></div>
          </div>

          <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--gray-500); margin-top: 6px;">
            <span>Category: ${m.category}</span>
            <span>Attempts: ${m.attempt_count}</span>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
    document.getElementById('stat-mastered-count').innerText = masteredCount;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Failed to load mastery data: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------------------
// 3. LEARNING PATH
// -------------------------------------------------------------------------
async function loadLearningPath() {
  const container = document.getElementById('path-container');
  try {
    const path = await apiFetch('/api/learning-paths/me');
    if (!path || !path.path_id) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 32px;">
          <p style="color: var(--gray-600); margin-bottom: 12px;">No active learning path found. Enroll in a course to initiate your trajectory.</p>
        </div>
      `;
      document.getElementById('stat-path-progress').innerText = '0%';
      return;
    }

    document.getElementById('stat-path-progress').innerText = `${path.progress_percentage}%`;

    let stepsHtml = '';
    path.steps.forEach(st => {
      let badgeColor = '#64748b';
      if (st.status === 'COMPLETED') badgeColor = '#10b981';
      else if (st.status === 'IN_PROGRESS') badgeColor = '#0ea5e9';

      stepsHtml += `
        <div style="display: flex; align-items: center; gap: 16px; padding: 14px 18px; border-bottom: 1px solid var(--gray-100); background: ${st.status === 'COMPLETED' ? '#f0fdf4' : 'var(--white)'};">
          <div style="width: 32px; height: 32px; border-radius: var(--radius-full); background: ${badgeColor}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem;">
            ${st.order}
          </div>
          <div style="flex: 1;">
            <div style="font-weight: 600; color: var(--gray-900); font-size: 0.95rem;">${st.title}</div>
            <div style="font-size: 0.8rem; color: var(--gray-500);">${st.course_title} (${st.format})</div>
          </div>
          <span class="role-badge" style="background: ${st.status === 'COMPLETED' ? '#d1fae5' : '#e0e7ff'}; color: ${badgeColor};">
            ${st.status}
          </span>
        </div>
      `;
    });

    container.innerHTML = `
      <div class="card" style="padding: 0; overflow: hidden;">
        <div style="padding: 20px 24px; border-bottom: 1px solid var(--gray-200); background: var(--gray-50); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h4 style="margin: 0; color: var(--gray-900);">${path.target_course_title}</h4>
            <span style="font-size: 0.8rem; color: var(--gray-500);">Trajectory ID: <code>${path.path_id}</code></span>
          </div>
          <div style="text-align: right;">
            <span style="font-size: 1.25rem; font-weight: 700; color: var(--primary);">${path.progress_percentage}%</span>
            <span class="role-badge" style="margin-left: 8px;">${path.status}</span>
          </div>
        </div>
        <div>${stepsHtml}</div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Failed to load path: ${err.message}</div>`;
  }
}

// -------------------------------------------------------------------------
// 4. COURSE CATALOG & PREREQUISITE GATING
// -------------------------------------------------------------------------
async function loadCourseCatalog() {
  const container = document.getElementById('courses-catalog-container');
  try {
    const courses = await apiFetch('/api/courses');
    let enrolledCount = 0;

    let html = '';
    courses.forEach(c => {
      if (c.is_enrolled) enrolledCount++;

      const isEligible = c.eligibility ? c.eligibility.is_eligible : true;
      const canTakeGate = c.eligibility ? c.eligibility.can_attempt_gating_assessment : true;
      const gatingAssessment = c.eligibility?.prerequisites_status?.[0]?.gating_assessment;

      let lockBadge = '';
      let actionBtn = '';

      if (c.is_enrolled) {
        actionBtn = `<span class="role-badge role-learner" style="padding: 6px 14px;">Enrolled (${c.enrollment_progress}%)</span>`;
      } else if (isEligible) {
        actionBtn = `<button onclick="enrollCourse('${c.course_id}')" class="btn btn-primary btn-sm">Enroll Now</button>`;
        lockBadge = `<span class="prereq-pill prereq-unlocked">🔓 Open / Unlocked</span>`;
      } else {
        lockBadge = `<span class="prereq-pill prereq-locked">🔒 Locked (Prerequisites Unmet)</span>`;
        // Check if gating assessment is eligible to take!
        if (canTakeGate && gatingAssessment) {
          actionBtn = `
            <button onclick="startAssessmentModal('${gatingAssessment.assessment_id}')" class="btn btn-outline btn-sm">
              🎯 Take Gating Quiz (${gatingAssessment.required_score}%)
            </button>
          `;
        } else {
          actionBtn = `<button disabled class="btn btn-secondary btn-sm" title="Complete prerequisites first">Locked</button>`;
        }
      }

      // Format prerequisite explanation
      let prereqExplanation = '';
      if (!isEligible && c.eligibility?.reasons?.length > 0) {
        prereqExplanation = `
          <div style="background: var(--danger-bg); border: 1px solid #fecaca; border-radius: var(--radius-sm); padding: 10px; margin: 12px 0; font-size: 0.8rem; color: var(--danger-text);">
            <strong>Prerequisites Required:</strong>
            <ul style="margin: 4px 0 0 16px;">
              ${c.eligibility.reasons.map(r => `<li>${r}</li>`).join('')}
            </ul>
          </div>
        `;
      }

      html += `
        <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-size: 0.8rem; font-weight: 700; color: var(--gray-500);">${c.code}</span>
              ${lockBadge}
            </div>

            <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--gray-900); margin-bottom: 8px;">
              ${c.title}
            </h4>

            <p style="font-size: 0.85rem; color: var(--gray-600); margin-bottom: 12px; line-height: 1.4;">
              ${c.description}
            </p>

            <div style="font-size: 0.8rem; color: var(--gray-500); margin-bottom: 8px;">
              Difficulty: <strong>${c.difficulty}</strong> | Modules: ${c.content_count}
            </div>

            ${prereqExplanation}
          </div>

          <div style="margin-top: 16px; pt-2; border-top: 1px solid var(--gray-100); display: flex; justify-content: space-between; align-items: center;">
            ${actionBtn}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
    document.getElementById('stat-enrolled-count').innerText = enrolledCount;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Failed to load courses: ${err.message}</div>`;
  }
}

async function enrollCourse(courseId) {
  try {
    const res = await apiFetch(`/api/courses/${courseId}/enroll`, { method: 'POST' });
    showToast(res.message, 'success');
    loadCourseCatalog();
    loadLearningPath();
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

// -------------------------------------------------------------------------
// 5. ASSESSMENT ATTEMPTS & RESULTS
// -------------------------------------------------------------------------
async function loadAssessmentHistory() {
  const tbody = document.getElementById('attempts-table-body');
  try {
    const attempts = await apiFetch('/api/assessments/results');
    if (!attempts || attempts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--gray-400);">No assessment attempts found.</td></tr>`;
      return;
    }

    let html = '';
    attempts.forEach(att => {
      const passBadge = att.passed
        ? `<span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASSED</span>`
        : `<span class="role-badge" style="background: var(--danger-bg); color: var(--danger-text);">FAILED</span>`;

      html += `
        <tr>
          <td><code>${att.attempt_id}</code></td>
          <td><strong>${att.assessment_title}</strong></td>
          <td>Attempt #${att.attempt_number}</td>
          <td><strong>${att.percentage}%</strong> (${att.score}/${att.max_score})</td>
          <td>${passBadge}</td>
          <td style="font-size: 0.8rem; color: var(--gray-500);">${new Date(att.completed_at).toLocaleString()}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: var(--danger);">Failed to load history: ${err.message}</td></tr>`;
  }
}

// -------------------------------------------------------------------------
// 6. INTERACTIVE ASSESSMENT RUNNER
// -------------------------------------------------------------------------
async function startAssessmentModal(assessmentId) {
  try {
    showToast('Initializing assessment environment...', 'info');
    const data = await apiFetch(`/api/assessments/${assessmentId}/start`, { method: 'POST' });

    activeQuizAttemptId = data.attempt_id;
    activeAssessmentId = data.assessment_id;
    activeQuestions = data.questions;

    document.getElementById('quiz-title').innerText = data.title;
    const body = document.getElementById('quiz-body');

    let questionsHtml = `
      <div style="background: var(--gray-50); border: 1px solid var(--gray-200); padding: 12px 16px; border-radius: var(--radius-sm); margin-bottom: 20px;">
        <span style="font-size: 0.85rem; color: var(--gray-600);">Attempt ID: <code>${data.attempt_id}</code> | Time Limit: ${data.time_limit_minutes} minutes</span>
      </div>
    `;

    data.questions.forEach((q, qIdx) => {
      let optionsHtml = '';
      q.options.forEach(opt => {
        optionsHtml += `
          <label style="display: flex; align-items: center; gap: 10px; padding: 10px 14px; border: 1px solid var(--gray-200); border-radius: var(--radius-sm); margin-bottom: 8px; cursor: pointer; transition: background 0.15s ease;">
            <input type="radio" name="q_${q.id}" value="${opt.key}" style="width: 18px; height: 18px;">
            <span style="font-weight: 500; color: var(--gray-800);">${opt.key}. ${opt.text}</span>
          </label>
        `;
      });

      questionsHtml += `
        <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--gray-200);">
          <h4 style="font-size: 1rem; font-weight: 600; color: var(--gray-900); margin-bottom: 12px;">
            Question ${q.order}: ${q.question_text}
          </h4>
          <div>${optionsHtml}</div>
        </div>
      `;
    });

    body.innerHTML = questionsHtml;
    openModal('assessment-modal');
  } catch (err) {
    showToast(err.message, 'danger');
  }
}

async function submitAssessmentAnswers() {
  const submitBtn = document.getElementById('quiz-submit-btn');
  submitBtn.disabled = true;
  submitBtn.innerText = 'Evaluating on Backend...';

  const responses = [];
  activeQuestions.forEach(q => {
    const selected = document.querySelector(`input[name="q_${q.id}"]:checked`);
    responses.push({
      question_id: q.id,
      selected_option: selected ? selected.value : ''
    });
  });

  try {
    const result = await apiFetch(`/api/assessments/${activeAssessmentId}/submit`, {
      method: 'POST',
      body: JSON.stringify({
        attempt_id: activeQuizAttemptId,
        responses: responses
      })
    });

    closeModal('assessment-modal');
    submitBtn.disabled = false;
    submitBtn.innerText = 'Submit for Grading';

    // Show verified result alert
    const statusMsg = result.passed ? 'PASSED ✅' : 'FAILED ❌';
    showToast(`Assessment ${statusMsg}: ${result.score_percentage}% achieved.`, result.passed ? 'success' : 'warning');

    // Reload dashboards
    loadMasteryData();
    loadCourseCatalog();
    loadAssessmentHistory();
    loadRecommendations();
  } catch (err) {
    showToast(err.message, 'danger');
    submitBtn.disabled = false;
    submitBtn.innerText = 'Submit for Grading';
  }
}

// -------------------------------------------------------------------------
// 7. SUPPORT TICKETS
// -------------------------------------------------------------------------
function openSupportTicketModal() {
  openModal('support-modal');
}

async function loadSupportTickets() {
  const tbody = document.getElementById('tickets-table-body');
  try {
    const tickets = await apiFetch('/api/support/tickets');
    if (!tickets || tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--gray-400);">No tickets submitted.</td></tr>`;
      return;
    }

    let html = '';
    tickets.forEach(t => {
      let stClass = 'role-support_staff';
      if (t.status === 'RESOLVED') stClass = 'role-learner';
      else if (t.status === 'ESCALATED') stClass = 'role-platform_admin';

      html += `
        <tr>
          <td><code>${t.ticket_id}</code></td>
          <td>${t.category}</td>
          <td><strong>${t.subject}</strong></td>
          <td><span class="role-badge ${stClass}">${t.status}</span></td>
          <td>${t.assigned_to_name || 'Unassigned'}</td>
          <td>${t.resolution || 'Pending investigation'}</td>
          <td style="font-size: 0.8rem; color: var(--gray-500);">${new Date(t.created_at).toLocaleDateString()}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--danger);">Failed to load tickets: ${err.message}</td></tr>`;
  }
}
