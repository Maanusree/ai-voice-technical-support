/**
 * Dashboard & Call Analytics Manager
 */
class DashboardManager {
  constructor() {
    this.init();
  }

  init() {
    this.loadAnalytics();
    this.loadSessions();
    this.loadTickets();

    const btnRefresh = document.getElementById('btnRefreshLogs');
    if (btnRefresh) btnRefresh.addEventListener('click', () => {
      this.loadAnalytics();
      this.loadSessions();
      this.loadTickets();
    });

    const btnExport = document.getElementById('btnExportCsv');
    if (btnExport) btnExport.addEventListener('click', () => {
      window.location.href = '/api/logs/export/csv';
    });

    const btnCloseModal = document.getElementById('btnCloseModal');
    if (btnCloseModal) {
      btnCloseModal.addEventListener('click', () => {
        const modal = document.getElementById('transcriptModal');
        if (modal) {
          modal.style.display = 'none';
          modal.classList.remove('active');
        }
      });
    }
  }

  async loadAnalytics() {
    try {
      const resp = await fetch('/api/logs/analytics');
      const data = await resp.json();

      const totalEl = document.getElementById('statTotalCalls');
      const resRateEl = document.getElementById('statResolutionRate');
      const escCountEl = document.getElementById('statEscalated');
      const avgDurEl = document.getElementById('statAvgDuration');

      if (totalEl) totalEl.innerText = data.total_calls || 0;
      if (resRateEl) resRateEl.innerText = `${data.resolution_rate || 0}%`;
      if (escCountEl) escCountEl.innerText = data.escalated_count || 0;
      if (avgDurEl) avgDurEl.innerText = `${Math.round(data.avg_duration_seconds || 0)}s`;
    } catch (e) {
      console.error('Error loading analytics:', e);
    }
  }

  async loadSessions() {
    const tableBody = document.getElementById('sessionsTableBody');
    if (!tableBody) return;

    try {
      const resp = await fetch('/api/logs/sessions?limit=50');
      const data = await resp.json();
      const sessions = data.sessions || [];

      if (sessions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No call logs recorded yet. Start a call to generate records.</td></tr>';
        return;
      }

      tableBody.innerHTML = sessions.map(s => {
        const dateStr = s.start_time ? new Date(s.start_time).toLocaleString() : 'N/A';
        const durStr = `${Math.round(s.duration_seconds || 0)}s`;
        const resStatus = s.resolution_status || 'in_progress';
        let badgeClass = 'warning';
        if (resStatus === 'resolved') badgeClass = 'success';
        if (resStatus === 'escalated') badgeClass = 'danger';

        return `
          <tr>
            <td><strong>${s.session_id}</strong></td>
            <td>${dateStr}</td>
            <td>${s.caller_number}</td>
            <td>${s.issue_category || 'General Inquiries'}</td>
            <td>${durStr}</td>
            <td><span class="badge ${badgeClass}">${resStatus.toUpperCase()}</span></td>
            <td>
              <button class="nav-tab" style="padding: 0.3rem 0.6rem; font-size: 0.75rem;" onclick="window.dashboardManager.viewTranscript('${s.session_id}')">
                📜 View Transcript (${s.turns.length})
              </button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error('Error loading sessions:', e);
    }
  }

  async loadTickets() {
    const container = document.getElementById('ticketsTableBody');
    if (!container) return;

    try {
      const resp = await fetch('/api/tickets');
      const data = await resp.json();
      const tickets = data.tickets || [];

      if (tickets.length === 0) {
        container.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No escalation tickets generated yet.</td></tr>';
        return;
      }

      container.innerHTML = tickets.map(t => {
        const prioClass = t.priority === 'CRITICAL' ? 'danger' : (t.priority === 'HIGH' ? 'warning' : 'info');
        const dateStr = new Date(t.created_at).toLocaleString();

        return `
          <tr>
            <td><strong>${t.ticket_id}</strong></td>
            <td>${dateStr}</td>
            <td><span class="badge ${prioClass}">${t.priority}</span></td>
            <td>${t.category}</td>
            <td>${t.reason_for_escalation}</td>
            <td><span class="badge info">${t.status}</span></td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error('Error loading tickets:', e);
    }
  }

  async viewTranscript(sessionId) {
    const modal = document.getElementById('transcriptModal');
    const modalBody = document.getElementById('modalTranscriptBody');
    const modalTitle = document.getElementById('modalTranscriptTitle');
    if (!modal || !modalBody) return;

    try {
      const resp = await fetch(`/api/logs/sessions/${sessionId}`);
      const session = await resp.json();

      if (modalTitle) modalTitle.innerText = `Call Transcript - ${sessionId}`;

      let contentHtml = `
        <div style="margin-bottom: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.3); border-radius: 8px; border: 1px solid var(--border-color);">
          <p><strong>Caller:</strong> ${session.caller_name} (${session.caller_number})</p>
          <p><strong>Category:</strong> ${session.issue_category}</p>
          <p><strong>Status:</strong> ${session.resolution_status} | <strong>Sentiment:</strong> ${session.sentiment}</p>
          ${session.escalation_ticket_id ? `<p style="color: var(--danger);"><strong>Escalation Ticket:</strong> ${session.escalation_ticket_id}</p>` : ''}
        </div>
        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
      `;

      if (session.turns && session.turns.length > 0) {
        session.turns.forEach(turn => {
          const isAssistant = turn.role === 'assistant';
          contentHtml += `
            <div style="padding: 0.85rem; border-radius: 8px; background: ${isAssistant ? 'rgba(30, 41, 59, 0.8)' : 'rgba(59, 130, 246, 0.15)'}; border-left: 4px solid ${isAssistant ? 'var(--accent-cyan)' : 'var(--accent-blue)'};">
              <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.25rem; display: flex; justify-content: space-between;">
                <strong>${isAssistant ? '👩‍💻 Support Specialist (Maanu)' : '👤 Caller'}</strong>
                <span>${turn.timestamp ? new Date(turn.timestamp).toLocaleTimeString() : ''}</span>
              </div>
              <div style="color: var(--text-primary); font-size: 0.92rem; line-height: 1.4;">${turn.text}</div>
            </div>
          `;
        });
      } else {
        contentHtml += `<p style="color: var(--text-muted); text-align: center;">No turns recorded for this call.</p>`;
      }

      contentHtml += `</div>`;
      modalBody.innerHTML = contentHtml;
      modal.style.display = 'flex';
      modal.classList.add('active');
    } catch (e) {
      console.error('Error loading transcript detail:', e);
    }
  }
}

window.DashboardManager = DashboardManager;
