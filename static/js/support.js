/**
 * Support Staff Dashboard Client Script
 */

let allTickets = [];

document.addEventListener('DOMContentLoaded', () => {
  loadSupportQueue();

  const resolveForm = document.getElementById('resolve-ticket-form');
  if (resolveForm) {
    resolveForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const ticketId = document.getElementById('resolve-ticket-id').value;
      const statusChoice = document.getElementById('resolve-status-choice').value;
      const resolution = document.getElementById('resolve-notes').value.trim();

      try {
        await apiFetch(`/api/support/tickets/${ticketId}/update`, {
          method: 'POST',
          body: JSON.stringify({ status: statusChoice, resolution: resolution })
        });
        showToast(`Ticket ${ticketId} updated.`, 'success');
        closeModal('resolve-ticket-modal');
        loadSupportQueue();
      } catch (err) {
        showToast(err.message, 'danger');
      }
    });
  }
});

async function loadSupportQueue() {
  const tbody = document.getElementById('support-tickets-body');
  try {
    allTickets = await apiFetch('/api/support/tickets');
    filterTickets();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color: var(--danger);">Failed to load tickets: ${err.message}</td></tr>`;
  }
}

function filterTickets() {
  const statusFilter = document.getElementById('filter-status').value;
  const catFilter = document.getElementById('filter-category').value;
  const tbody = document.getElementById('support-tickets-body');

  let filtered = allTickets;
  if (statusFilter !== 'ALL') {
    filtered = filtered.filter(t => t.status === statusFilter);
  }
  if (catFilter !== 'ALL') {
    filtered = filtered.filter(t => t.category === catFilter);
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--gray-400);">No tickets match the selected filters.</td></tr>`;
    return;
  }

  let html = '';
  filtered.forEach(t => {
    let stClass = 'role-support_staff';
    if (t.status === 'RESOLVED') stClass = 'role-learner';
    else if (t.status === 'ESCALATED') stClass = 'role-platform_admin';

    html += `
      <tr>
        <td><code>${t.ticket_id}</code></td>
        <td><strong>${t.learner_id}</strong> (${t.learner_username})</td>
        <td>${t.category}</td>
        <td>${t.subject}</td>
        <td><span class="role-badge ${stClass}">${t.status}</span></td>
        <td>${t.assigned_to_name || 'Unassigned'}</td>
        <td style="font-size: 0.8rem; color: var(--gray-500);">${new Date(t.created_at).toLocaleDateString()}</td>
        <td>
          <button onclick="openResolveModal('${t.ticket_id}')" class="btn btn-secondary btn-sm" style="font-size: 0.75rem;">
            🔍 Investigate
          </button>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;
}

function openResolveModal(ticketId) {
  const ticket = allTickets.find(t => t.ticket_id === ticketId);
  if (!ticket) return;

  document.getElementById('resolve-ticket-id').value = ticket.ticket_id;
  document.getElementById('resolve-modal-title').innerText = `Ticket ${ticket.ticket_id}: ${ticket.subject}`;
  document.getElementById('resolve-ticket-meta').innerText = `Submitted by ${ticket.learner_id} | Category: ${ticket.category} | Current Status: ${ticket.status}`;
  document.getElementById('resolve-ticket-desc').innerText = ticket.description;
  document.getElementById('resolve-status-choice').value = ticket.status === 'OPEN' ? 'IN_PROGRESS' : ticket.status;
  document.getElementById('resolve-notes').value = ticket.resolution || '';

  openModal('resolve-ticket-modal');
}
