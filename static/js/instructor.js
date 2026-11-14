/**
 * Instructor Dashboard Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  loadInstructorCourses();
  loadInstructorSkills();
  loadInstructorAssessments();
  loadLearnerProgress();

  // Create course handler
  const courseForm = document.getElementById('create-course-form');
  if (courseForm) {
    courseForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        course_id: document.getElementById('course_id').value.trim(),
        title: document.getElementById('course_title').value.trim(),
        code: document.getElementById('course_code').value.trim(),
        difficulty: document.getElementById('course_difficulty').value,
        is_advanced: document.getElementById('course_is_advanced').checked,
        description: document.getElementById('course_description').value.trim()
      };

      try {
        await apiFetch('/api/courses', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast('Course created successfully!', 'success');
        closeModal('new-course-modal');
        courseForm.reset();
        loadInstructorCourses();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }

  // Create skill handler
  const skillForm = document.getElementById('create-skill-form');
  if (skillForm) {
    skillForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        skill_id: document.getElementById('skill_id').value.trim(),
        name: document.getElementById('skill_name').value.trim(),
        code: document.getElementById('skill_code').value.trim(),
        category: document.getElementById('skill_category').value.trim(),
        description: document.getElementById('skill_description').value.trim()
      };

      try {
        await apiFetch('/api/skills', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast('Skill created successfully!', 'success');
        closeModal('new-skill-modal');
        skillForm.reset();
        loadInstructorSkills();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }
});

async function loadInstructorCourses() {
  const container = document.getElementById('instructor-courses-container');
  try {
    const courses = await apiFetch('/api/courses');
    let html = '';
    courses.forEach(c => {
      const advBadge = c.is_advanced
        ? `<span class="role-badge role-academic_admin">Prerequisite Gated</span>`
        : `<span class="role-badge role-learner">Fundamental</span>`;

      html += `
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 0.8rem; font-weight: 700; color: var(--gray-500);">${c.code}</span>
            ${advBadge}
          </div>
          <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--gray-900); margin-bottom: 8px;">${c.title}</h4>
          <p style="font-size: 0.85rem; color: var(--gray-600); margin-bottom: 12px;">${c.description}</p>
          <div style="font-size: 0.8rem; color: var(--gray-500); border-top: 1px solid var(--gray-100); pt-2; margin-top: 12px;">
            Modules: <strong>${c.content_count}</strong> | Difficulty: <strong>${c.difficulty}</strong>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Failed to load courses: ${err.message}</div>`;
  }
}

async function loadInstructorSkills() {
  const tbody = document.getElementById('skills-table-body');
  try {
    const skills = await apiFetch('/api/skills');
    let html = '';
    skills.forEach(s => {
      html += `
        <tr>
          <td><code>${s.skill_id}</code></td>
          <td><strong>${s.name}</strong></td>
          <td><code>${s.code}</code></td>
          <td>${s.category}</td>
          <td style="font-size: 0.85rem; color: var(--gray-600);">${s.description || '-'}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="color: var(--danger);">Failed: ${err.message}</td></tr>`;
  }
}

async function loadInstructorAssessments() {
  const tbody = document.getElementById('assessments-table-body');
  try {
    const assessments = await apiFetch('/api/assessments');
    let html = '';
    assessments.forEach(a => {
      const gateBadge = a.is_prerequisite_gate
        ? `<span class="role-badge role-platform_admin">YES (Gating)</span>`
        : `<span class="role-badge role-learner">Standard Quiz</span>`;

      html += `
        <tr>
          <td><code>${a.assessment_id}</code></td>
          <td><strong>${a.title}</strong></td>
          <td>${a.course_title}</td>
          <td>${a.skill_name}</td>
          <td><strong>${a.passing_percentage}%</strong></td>
          <td>${gateBadge}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: var(--danger);">Failed: ${err.message}</td></tr>`;
  }
}

async function loadLearnerProgress() {
  const tbody = document.getElementById('attempts-monitor-body');
  try {
    const attempts = await apiFetch('/api/assessments/results');
    let html = '';
    attempts.forEach(att => {
      const isAtRisk = (att.percentage < 50.0);
      const flagBadge = isAtRisk
        ? `<span class="role-badge" style="background: var(--danger-bg); color: var(--danger-text);">⚠️ At Risk (&lt;50%)</span>`
        : `<span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">On Track</span>`;

      html += `
        <tr>
          <td><code>${att.attempt_id}</code></td>
          <td>Learner ${att.learner}</td>
          <td>${att.assessment_title}</td>
          <td><strong>${att.percentage}%</strong></td>
          <td>${att.passed ? 'PASSED' : 'FAILED'}</td>
          <td>${flagBadge}</td>
          <td style="font-size: 0.8rem; color: var(--gray-500);">${new Date(att.completed_at).toLocaleDateString()}</td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--danger);">Failed: ${err.message}</td></tr>`;
  }
}
