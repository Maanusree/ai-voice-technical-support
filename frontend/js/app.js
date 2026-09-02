/**
 * Main Application Orchestrator
 */
document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 Initializing InnoAssist Voice Support Interface...');

  // 1. Initialize Visualizer
  const visualizer = new AudioVisualizer('audioCanvas');

  // 2. Initialize Phone Call Manager
  const phoneCall = new PhoneCallManager(visualizer);
  window.phoneCall = phoneCall;

  // 3. Initialize Dashboard Manager
  const dashboard = new DashboardManager();
  window.dashboardManager = dashboard;

  // 4. Initialize Knowledge Base Explorer
  const kbExplorer = new KnowledgeBaseExplorer();
  window.kbExplorer = kbExplorer;

  // 5. Setup Tab Navigation
  const navTabs = document.querySelectorAll('.nav-tab[data-tab]');
  const tabContents = document.querySelectorAll('.tab-content');

  navTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTabId = tab.getAttribute('data-tab');

      navTabs.forEach(t => t.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetContent = document.getElementById(targetTabId);
      if (targetContent) {
        targetContent.classList.add('active');
      }

      if (targetTabId === 'tab-dashboard') {
        dashboard.loadAnalytics();
        dashboard.loadSessions();
        dashboard.loadTickets();
      } else if (targetTabId === 'tab-kb') {
        kbExplorer.loadArticles();
      }
    });
  });

  // 6. Pre-loaded Scenario Quick-Launch Cards
  const scenarioBtns = document.querySelectorAll('.scenario-card-btn[data-prompt]');
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const promptText = btn.getAttribute('data-prompt');
      console.log('Triggering scenario prompt:', promptText);

      if (phoneCall.callState !== 'connected' && phoneCall.callState !== 'escalating') {
        await phoneCall.startCall();
        // Give greeting audio a brief moment then inject the scenario statement
        setTimeout(() => {
          phoneCall.handleUserSpokenMessage(promptText);
        }, 800);
      } else {
        phoneCall.handleUserSpokenMessage(promptText);
      }
    });
  });

  // 7. Settings Form Configuration
  const settingsForm = document.getElementById('settingsForm');
  if (settingsForm) {
    // Load current config from server
    fetch('/api/config')
      .then(res => res.json())
      .then(conf => {
        const provSelect = document.getElementById('llmProviderSelect');
        if (provSelect) provSelect.value = conf.current_provider || 'offline';
      })
      .catch(e => console.warn('Config fetch warning:', e));

    settingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const prov = document.getElementById('llmProviderSelect').value;
      const gemKey = document.getElementById('geminiApiKeyInput').value;
      const openKey = document.getElementById('openaiApiKeyInput').value;
      const groqKey = document.getElementById('groqApiKeyInput').value;

      try {
        const resp = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            llm_provider: prov,
            gemini_key: gemKey,
            openai_key: openKey,
            groq_key: groqKey
          })
        });
        const result = await resp.json();
        alert(`✅ AI Engine updated to: ${result.provider.toUpperCase()}`);
      } catch (err) {
        alert('Failed to save settings');
      }
    });
  }

  // 8. Test Voice Audio Button
  const btnTestVoice = document.getElementById('btnTestVoice');
  if (btnTestVoice) {
    btnTestVoice.addEventListener('click', async () => {
      const testText = "Hello! InnoAssist voice synthesis system is working properly.";
      try {
        const resp = await fetch('/api/calls/synthesize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: testText })
        });
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        if (visualizer) visualizer.setMode('speaking');
        audio.onended = () => visualizer.setMode('idle');
        audio.play();
      } catch (e) {
        alert('Voice synthesis test failed');
      }
    });
  }

  // 8b. Real Phone Outbound Calling Modal & Execution
  const phoneCallModal = document.getElementById('phoneCallModal');
  const btnTriggerRealPhoneCall = document.getElementById('btnTriggerRealPhoneCall');
  const btnClosePhoneCallModal = document.getElementById('btnClosePhoneCallModal');
  const btnCancelPhoneCallModal = document.getElementById('btnCancelPhoneCallModal');
  const btnConfirmTriggerCall = document.getElementById('btnConfirmTriggerCall');
  const modalInputPhoneNumber = document.getElementById('modalInputPhoneNumber');
  const triggerCallStatus = document.getElementById('triggerCallStatus');
  const twilioSettingsForm = document.getElementById('twilioSettingsForm');

  async function executeOutboundCall(payload = {}) {
    if (triggerCallStatus) triggerCallStatus.innerText = '⏳ Contacting Twilio Gateway...';
    try {
      const resp = await fetch('/api/telephony/trigger-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (resp.ok && data.status === 'success') {
        if (triggerCallStatus) triggerCallStatus.innerText = `📞 Calling ${payload.to_phone || '+91 74182 14150'}! Check your phone!`;
        alert(`🎉 ${data.message}\n\nPick up your phone to speak with Maanu!`);
      } else {
        if (triggerCallStatus) triggerCallStatus.innerText = '❌ Click AI Settings to paste Twilio SID/Token';
        alert(`⚠️ ${data.message || 'Please paste your Twilio Account SID and Auth Token in the AI Settings tab.'}`);
        // Switch to settings tab automatically
        const settingsTab = document.querySelector('[data-tab="tab-settings"]');
        if (settingsTab) settingsTab.click();
      }
    } catch (e) {
      if (triggerCallStatus) triggerCallStatus.innerText = '❌ Connection failed';
      alert('Error triggering outbound phone call.');
    }
  }

  function openPhoneCallModal() {
    const modal = document.getElementById('phoneCallModal');
    const input = document.getElementById('modalInputPhoneNumber');
    if (modal) {
      modal.classList.add('active');
      if (input) {
        input.focus();
        input.select();
      }
    }
  }

  function closePhoneCallModal() {
    const modal = document.getElementById('phoneCallModal');
    if (modal) {
      modal.classList.remove('active');
    }
  }

  window.openPhoneCallModal = openPhoneCallModal;
  window.closePhoneCallModal = closePhoneCallModal;

  if (btnTriggerRealPhoneCall) {
    btnTriggerRealPhoneCall.addEventListener('click', () => {
      openPhoneCallModal();
    });
  }

  if (btnClosePhoneCallModal) btnClosePhoneCallModal.addEventListener('click', closePhoneCallModal);
  if (btnCancelPhoneCallModal) btnCancelPhoneCallModal.addEventListener('click', closePhoneCallModal);
  if (phoneCallModal) {
    phoneCallModal.addEventListener('click', (e) => {
      if (e.target === phoneCallModal) closePhoneCallModal();
    });
  }

  if (btnConfirmTriggerCall) {
    btnConfirmTriggerCall.addEventListener('click', () => {
      const enteredPhone = modalInputPhoneNumber?.value?.trim() || '+917418214150';
      if (!enteredPhone) {
        alert('Please enter your mobile phone number.');
        return;
      }
      closePhoneCallModal();
      executeOutboundCall({ to_phone: enteredPhone });
    });
  }

  if (modalInputPhoneNumber) {
    modalInputPhoneNumber.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        btnConfirmTriggerCall.click();
      }
    });
  }

  if (twilioSettingsForm) {
    twilioSettingsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const sid = document.getElementById('settingTwilioSid')?.value?.trim() || '';
      const token = document.getElementById('settingTwilioToken')?.value?.trim() || '';
      const from = document.getElementById('settingTwilioFrom')?.value?.trim() || '+19035322035';
      const to = document.getElementById('settingTwilioTo')?.value?.trim() || '+917418214150';
      const ngrok = document.getElementById('settingNgrokUrl')?.value?.trim() || 'https://snooze-prominent-overvalue.ngrok-free.dev';

      executeOutboundCall({
        account_sid: sid,
        auth_token: token,
        from_phone: from,
        to_phone: to,
        ngrok_url: ngrok
      });
    });
  }

  // 9. Real-Time Phone Call Sync Loop (Throttled & checks tab visibility)
  let lastSyncedTurnCount = 0;
  let lastSyncedSessionId = null;

  setInterval(async () => {
    if (document.hidden) return; // Don't poll if browser tab is hidden/minimized
    try {
      const resp = await fetch('/api/logs/latest');
      if (!resp.ok) return;
      const data = await resp.json();
      if (!data.session) return;

      const session = data.session;
      const isTelephonyCall = session.caller_number !== '+1-800-555-0199' || session.caller_name === 'Mobile Caller';

      // If new session or new turns arrived from a real phone call
      if (session.session_id !== lastSyncedSessionId) {
        lastSyncedSessionId = session.session_id;
        lastSyncedTurnCount = 0;
      }

      if (session.turns && session.turns.length > lastSyncedTurnCount) {
        const newTurns = session.turns.slice(lastSyncedTurnCount);
        lastSyncedTurnCount = session.turns.length;

        // If phone call is active, update status and append turns to the HUD
        if (isTelephonyCall) {
          const statusTextEl = document.getElementById('callStatusText');
          const statusDotEl = document.getElementById('callStatusDot');
          if (statusTextEl) statusTextEl.innerText = `📱 Live Phone Call: ${session.caller_number} (${session.status.toUpperCase()})`;
          if (statusDotEl) statusDotEl.className = 'status-dot speaking';

          newTurns.forEach(turn => {
            if (phoneCall && phoneCall.transcriptFeedEl) {
              phoneCall.appendTranscriptBubble(turn.role, turn.text, turn.latency_ms || {}, turn.intent);
            }
          });

          // Trigger visualizer animation
          if (visualizer) {
            visualizer.setMode(session.status === 'escalating' ? 'escalating' : 'speaking');
            setTimeout(() => visualizer.setMode('idle'), 2500);
          }

          // Auto refresh dashboard tables
          if (dashboard) {
            dashboard.loadAnalytics();
            dashboard.loadSessions();
            dashboard.loadTickets();
          }
        }
      }
    } catch (e) {
      // Background sync silent catch
    }
  }, 8000);

  console.log('✅ Interface ready with Live Phone Call Sync!');
});
