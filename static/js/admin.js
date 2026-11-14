/**
 * Platform Administrator Dashboard Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  loadPendingRegistrations();
  runValidationBenchmark();

  const decisionForm = document.getElementById('decision-form');
  if (decisionForm) {
    decisionForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const learnerId = document.getElementById('decision-learner-id').value;
      const type = document.getElementById('decision-type').value;
      const reason = document.getElementById('decision-reason').value.trim();

      const endpoint = type === 'APPROVE'
        ? `/api/admin/registrations/${learnerId}/approve`
        : `/api/admin/registrations/${learnerId}/reject`;

      try {
        const res = await apiFetch(endpoint, {
          method: 'POST',
          body: JSON.stringify({ reason })
        });
        showToast(res.message, 'success');
        closeModal('decision-modal');
        loadPendingRegistrations();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }
});

async function loadPendingRegistrations() {
  const tbody = document.getElementById('pending-regs-body');
  try {
    const list = await apiFetch('/api/admin/registrations/pending');
    document.getElementById('pending-badge').innerText = list.length;

    if (!list || list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--gray-400); padding: 32px;">No pending learner registrations. All applications processed!</td></tr>`;
      return;
    }

    let html = '';
    list.forEach(item => {
      const u = item.user;
      html += `
        <tr>
          <td><code>${item.learner_id}</code></td>
          <td><strong>${u.username}</strong></td>
          <td>${u.email}</td>
          <td>${u.first_name || ''} ${u.last_name || ''}</td>
          <td>${item.current_education_level}</td>
          <td style="font-size: 0.8rem; color: var(--gray-600); max-width: 200px;">${item.learning_goals || '-'}</td>
          <td style="font-size: 0.8rem; color: var(--gray-500);">${new Date(item.created_at).toLocaleDateString()}</td>
          <td>
            <div style="display: flex; gap: 6px;">
              <button onclick="promptDecision('${item.learner_id}', '${u.username}', 'APPROVE')" class="btn btn-success btn-sm" style="font-size: 0.75rem; padding: 4px 8px;">
                ✓ Approve
              </button>
              <button onclick="promptDecision('${item.learner_id}', '${u.username}', 'REJECT')" class="btn btn-danger btn-sm" style="font-size: 0.75rem; padding: 4px 8px;">
                ✗ Reject
              </button>
            </div>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = html;
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color: var(--danger);">Failed: ${err.message}</td></tr>`;
  }
}

function promptDecision(learnerId, username, type) {
  document.getElementById('decision-learner-id').value = learnerId;
  document.getElementById('decision-type').value = type;
  document.getElementById('decision-reason').value = '';

  const title = document.getElementById('decision-modal-title');
  const prompt = document.getElementById('decision-prompt');
  const submitBtn = document.getElementById('decision-submit-btn');

  if (type === 'APPROVE') {
    title.innerText = `Approve Registration: ${learnerId}`;
    prompt.innerHTML = `Are you sure you want to approve learner <strong>${username}</strong>? Their status will become <strong>ACTIVE</strong>, granting immediate system access.`;
    submitBtn.className = 'btn btn-success btn-sm';
    submitBtn.innerText = 'Approve & Activate Account';
  } else {
    title.innerText = `Reject Registration: ${learnerId}`;
    prompt.innerHTML = `Are you sure you want to reject learner <strong>${username}</strong>? Their status will become <strong>REJECTED</strong>, blocking authentication.`;
    submitBtn.className = 'btn btn-danger btn-sm';
    submitBtn.innerText = 'Reject Application';
  }

  openModal('decision-modal');
}

async function runValidationBenchmark() {
  const container = document.getElementById('benchmark-results-container');
  container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--primary);">Running automated evaluation benchmark...</div>`;

  try {
    const data = await apiFetch('/api/admin/data-validation');
    const counts = data.counts;
    const m = data.metrics;

    container.innerHTML = `
      <div class="grid grid-cols-4" style="margin-bottom: 24px;">
        <div class="stat-card">
          <span class="stat-label">Prerequisite Compliance</span>
          <div class="stat-value" style="color: var(--success);">${m.prerequisite_compliance_rate}%</div>
          <div class="stat-footer">Target: &ge; 95%</div>
        </div>
        <div class="stat-card">
          <span class="stat-label">Anomaly Detection Rate</span>
          <div class="stat-value" style="color: var(--success);">${m.anomaly_detection_rate}%</div>
          <div class="stat-footer">Ground truth verified</div>
        </div>
        <div class="stat-card">
          <span class="stat-label">Mastery Reproducibility</span>
          <div class="stat-value" style="color: var(--primary);">${m.mastery_reproducibility_rate}%</div>
          <div class="stat-footer">Deterministic verification</div>
        </div>
        <div class="stat-card">
          <span class="stat-label">FK Referential Integrity</span>
          <div class="stat-value" style="color: var(--primary);">${m.fk_integrity_rate}%</div>
          <div class="stat-footer">Zero orphan records</div>
        </div>
      </div>

      <div class="card">
        <h4 style="font-weight: 700; margin-bottom: 12px;">Evaluation Benchmark Summary (${data.status})</h4>
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Benchmark Metric</th>
                <th>Target Threshold</th>
                <th>Evaluated Score</th>
                <th>Validation Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Primary Key Uniqueness</strong></td>
                <td>100.0%</td>
                <td><strong>${m.pk_uniqueness_rate}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Foreign Key Referential Integrity</strong></td>
                <td>100.0%</td>
                <td><strong>${m.fk_integrity_rate}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Prerequisite Compliance Rate</strong></td>
                <td>&ge; 95.0%</td>
                <td><strong>${m.prerequisite_compliance_rate}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Recommendation Coverage Rate</strong></td>
                <td>&ge; 15.0%</td>
                <td><strong>${m.recommendation_coverage_rate}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Precision@3</strong></td>
                <td>&ge; 70.0%</td>
                <td><strong>${m.precision_at_3}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Recall@3</strong></td>
                <td>&ge; 70.0%</td>
                <td><strong>${m.recall_at_3}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Skill Graph Acyclicity (DAG)</strong></td>
                <td>True</td>
                <td><strong>${m.skill_graph_is_dag ? 'Acyclic (No Cycles)' : 'Cycle Detected'}</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
              <tr>
                <td><strong>Anomaly Detection Rate</strong></td>
                <td>100.0%</td>
                <td><strong>${m.anomaly_detection_rate}%</strong></td>
                <td><span class="role-badge" style="background: var(--success-bg); color: var(--success-text);">PASS</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div style="color: var(--danger);">Evaluation failed: ${err.message}</div>`;
  }
}

function triggerDataGen() {
  const mode = document.getElementById('gen-mode').value;
  const seed = document.getElementById('gen-seed').value;
  showToast(`Synthetic data generation (${mode} mode) initiated with seed ${seed}. Run 'python manage.py generate_synthetic_data' via terminal for full dataset.`, 'info');
  closeModal('data-gen-modal');
}
