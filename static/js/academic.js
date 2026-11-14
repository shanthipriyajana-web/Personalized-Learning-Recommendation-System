/**
 * Academic Administrator Dashboard Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  loadAcademicAnalytics();
});

async function loadAcademicAnalytics() {
  try {
    const data = await apiFetch('/api/admin/analytics');
    document.getElementById('acad-learners').innerText = data.active_learners;
    document.getElementById('acad-enrollments').innerText = data.total_enrollments;
    document.getElementById('acad-completion-rate').innerText = `${data.completion_rate_percentage}%`;
    document.getElementById('acad-avg-mastery').innerText = `${data.average_mastery_percentage}%`;

    const tbody = document.getElementById('skill-gaps-table-body');
    if (!data.skill_gaps || data.skill_gaps.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--gray-400);">No significant skill gaps detected.</td></tr>`;
      return;
    }

    let html = '';
    data.skill_gaps.forEach(gap => {
      html += `
        <tr>
          <td><code>${gap.skill__code}</code></td>
          <td><strong>${gap.skill__name}</strong></td>
          <td><span class="role-badge role-platform_admin">${gap.c} learners</span></td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    showToast(`Failed to load academic metrics: ${err.message}`, 'danger');
  }
}

function downloadAcademicReport() {
  showToast('Exporting academic report CSV...', 'info');
  // Simple CSV trigger
  window.open('/api/admin/data-validation', '_blank');
}
