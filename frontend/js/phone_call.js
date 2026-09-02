/**
 * Phone Call Simulator & Voice Interaction Manager
 */
class PhoneCallManager {
  constructor(visualizer) {
    this.visualizer = visualizer;
    this.sessionId = null;
    this.callState = 'idle'; // 'idle', 'ringing', 'connected', 'on_hold', 'escalating', 'ended'
    this.isMuted = false;
    this.isOnHold = false;
    this.isRecording = false;
    this.callTimerInterval = null;
    this.callSeconds = 0;
    this.currentAudio = null;
    this.lastSpokenText = '';
    this.mediaStream = null;

    // Speech Recognition Setup
    this.recognition = null;
    this.initSpeechRecognition();

    // DOM Elements
    this.avatarEl = document.getElementById('callerAvatar');
    this.statusPillEl = document.getElementById('callStatusPill');
    this.statusDotEl = document.getElementById('callStatusDot');
    this.statusTextEl = document.getElementById('callStatusText');
    this.callTimerEl = document.getElementById('callTimer');
    this.transcriptFeedEl = document.getElementById('transcriptFeed');
    this.micToggleBtn = document.getElementById('btnToggleMic');
    this.btnStartCall = document.getElementById('btnStartCall');
    this.btnEndCall = document.getElementById('btnEndCall');
    this.btnHoldCall = document.getElementById('btnHoldCall');
    this.btnMuteCall = document.getElementById('btnMuteCall');
    this.btnEscalateCall = document.getElementById('btnEscalateCall');

    this.bindEvents();
  }

  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
          this.isRecording = true;
          this.updateMicButtonUI(true);
          if (this.visualizer) this.visualizer.setMode('listening');
          this.setStatus('Listening to your microphone...', 'active');
        };

        this.recognition.onresult = (event) => {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }

          const activeInput = document.getElementById('chatInput');
          const recognized = finalTranscript || interimTranscript;

          if (recognized) {
            this.lastSpokenText = recognized.trim();
            if (activeInput) {
              activeInput.value = this.lastSpokenText;
            }
          }
        };

        this.recognition.onerror = (event) => {
          console.warn('Speech recognition error:', event.error);
          if (event.error === 'not-allowed') {
            this.appendSystemNotice('⚠️ Microphone access blocked. Please click the Lock/Camera icon in your browser address bar and set Microphone to "Allow".');
          }
          this.isRecording = false;
          this.updateMicButtonUI(false);
          if (this.visualizer) this.visualizer.setMode('idle');
        };

        this.recognition.onend = () => {
          this.isRecording = false;
          this.updateMicButtonUI(false);

          // If we captured speech text, send it automatically!
          if (this.lastSpokenText && this.lastSpokenText.trim()) {
            const toSend = this.lastSpokenText.trim();
            this.lastSpokenText = '';
            const activeInput = document.getElementById('chatInput');
            if (activeInput) activeInput.value = '';
            this.handleUserSpokenMessage(toSend);
          } else {
            if (this.callState === 'connected' && (!this.currentAudio || this.currentAudio.paused)) {
              if (this.visualizer) this.visualizer.setMode('idle');
              this.setStatus('Connected - Ready', 'active');
            }
          }
        };
      } catch (e) {
        console.warn('Speech recognition init error:', e);
      }
    } else {
      console.warn('Speech recognition is not supported in this browser. Text input is active.');
    }
  }

  bindEvents() {
    if (this.btnStartCall) this.btnStartCall.addEventListener('click', () => this.startCall());
    if (this.btnEndCall) this.btnEndCall.addEventListener('click', () => this.endCall());
    if (this.btnHoldCall) this.btnHoldCall.addEventListener('click', () => this.toggleHold());
    if (this.btnMuteCall) this.btnMuteCall.addEventListener('click', () => this.toggleMute());
    if (this.btnEscalateCall) this.btnEscalateCall.addEventListener('click', () => this.escalateCall());
    if (this.micToggleBtn) this.micToggleBtn.addEventListener('click', () => this.toggleMic());

    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        if (this.recognition) {
          this.recognition.lang = e.target.value;
          this.appendSystemNotice(`🌐 Language switched to: ${e.target.options[e.target.selectedIndex].text}`);
        }
      });
    }

    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
      chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('chatInput');
        if (input && input.value.trim()) {
          const msg = input.value.trim();
          input.value = '';
          this.handleUserSpokenMessage(msg);
        }
      });
    }
  }

  async startCall(callerNumber = '+1-800-555-0199', callerName = 'Customer') {
    this.setStatus('Connecting to Maanu (AI Support)...', 'thinking');
    if (this.visualizer) this.visualizer.setMode('thinking');
    if (this.avatarEl) this.avatarEl.classList.add('active');

    try {
      const resp = await fetch('/api/calls/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caller_number: callerNumber, caller_name: callerName, generate_audio: true })
      });
      const data = await resp.json();

      this.sessionId = data.session_id;
      this.callState = 'connected';
      this.startTimer();
      this.updateCallControlsUI();
      this.setStatus('Maanu is Speaking...', 'speaking');
      if (this.avatarEl) this.avatarEl.classList.add('speaking');

      // Add Greeting to HUD
      this.appendTranscriptBubble('assistant', data.greeting, { tts: 120 });

      // Play Greeting Audio in background without blocking interaction
      if (data.audio_base64) {
        this.playAudioFromBase64(data.audio_base64);
      } else {
        this.speakBrowserFallback(data.greeting);
      }

      this.setStatus('Connected - Speak or Click a Scenario', 'active');
      if (this.visualizer) this.visualizer.setMode('idle');

    } catch (err) {
      console.error('Error starting call:', err);
      this.setStatus('Connection Failed - Check Backend', 'escalating');
      alert('Could not start call. Ensure the server is running on http://127.0.0.1:8000');
    }
  }

  async handleUserSpokenMessage(text) {
    if (!text || !text.trim()) return;

    if (this.callState !== 'connected' && this.callState !== 'escalating') {
      await this.startCall();
      await new Promise(r => setTimeout(r, 600));
    }

    if (this.isMuted) {
      this.appendSystemNotice('🔇 Microphone is muted. Click "Unmute" to speak.');
      return;
    }

    // Append User turn to HUD
    this.appendTranscriptBubble('user', text);
    this.setStatus('Maanu is diagnosing your issue...', 'thinking');
    if (this.visualizer) this.visualizer.setMode('thinking');

    try {
      const resp = await fetch('/api/calls/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.sessionId,
          message: text,
          generate_audio: true,
          stt_latency_ms: 12.0
        })
      });
      const data = await resp.json();

      // Handle Escalation state
      if (data.should_escalate) {
        this.callState = 'escalating';
        this.setStatus(`🚨 Escalating to Human Support (${data.ticket_id})`, 'escalating');
        if (this.visualizer) this.visualizer.setMode('escalating');
        if (this.avatarEl) this.avatarEl.classList.add('escalating');
        this.appendSystemNotice(`🚨 Human Escalation Triggered! Tier-2 Ticket ID: ${data.ticket_id}. Transferring call...`);
      } else {
        this.setStatus('Maanu is Speaking...', 'speaking');
        if (this.visualizer) this.visualizer.setMode('speaking');
        if (this.avatarEl) this.avatarEl.classList.add('speaking');
      }

      // Append Assistant turn to HUD
      this.appendTranscriptBubble('assistant', data.text, data.latency, data.intent);

      // Play Audio response
      if (data.audio_base64) {
        await this.playAudioFromBase64(data.audio_base64);
      } else {
        await this.speakBrowserFallback(data.text);
      }

      if (this.avatarEl) this.avatarEl.classList.remove('speaking');

      if (data.is_resolved) {
        this.appendSystemNotice('✅ Issue marked as Resolved by customer.');
      }

      if (this.callState === 'connected') {
        this.setStatus('Connected - Listening to your reply', 'active');
        if (this.visualizer) this.visualizer.setMode('idle');
      }

      // Refresh background logs
      if (window.dashboardManager) {
        window.dashboardManager.loadAnalytics();
        window.dashboardManager.loadSessions();
      }

    } catch (err) {
      console.error('Error processing message:', err);
      this.setStatus('Error processing request', 'escalating');
      this.appendSystemNotice('❌ System error communicating with AI agent.');
    }
  }

  async playAudioFromBase64(base64Str) {
    return new Promise((resolve) => {
      try {
        if (this.currentAudio) {
          this.currentAudio.pause();
        }
        const audioUrl = `data:audio/mp3;base64,${base64Str}`;
        this.currentAudio = new Audio(audioUrl);
        if (this.visualizer) this.visualizer.setMode('speaking');

        this.currentAudio.onended = () => {
          if (this.visualizer) this.visualizer.setMode('idle');
          if (this.callState === 'connected' && !this.isMuted) {
            this.startListening();
          }
          resolve();
        };

        this.currentAudio.onerror = (e) => {
          console.warn('Audio playback error:', e);
          if (this.visualizer) this.visualizer.setMode('idle');
          if (this.callState === 'connected' && !this.isMuted) {
            this.startListening();
          }
          resolve();
        };

        const playPromise = this.currentAudio.play();
        if (playPromise !== undefined) {
          playPromise.catch((e) => {
            console.warn('Audio auto-play policy:', e);
            if (this.visualizer) this.visualizer.setMode('idle');
            if (this.callState === 'connected' && !this.isMuted) {
              this.startListening();
            }
            resolve();
          });
        }
      } catch (err) {
        console.error('Audio decode failure:', err);
        if (this.visualizer) this.visualizer.setMode('idle');
        resolve();
      }
    });
  }

  startListening() {
    if (this.recognition && !this.isRecording && !this.isMuted && this.callState === 'connected') {
      try {
        this.lastSpokenText = '';
        this.recognition.start();
        this.isRecording = true;
        this.updateMicButtonUI(true);
        if (this.visualizer) this.visualizer.setMode('listening');
        this.setStatus('Listening to your microphone... Speak now!', 'active');
      } catch (e) {
        console.warn('Recognition start notification:', e);
      }
    }
  }

  speakBrowserFallback(text) {
    return new Promise((resolve) => {
      if (!('speechSynthesis' in window)) {
        resolve();
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        if (this.visualizer) this.visualizer.setMode('speaking');
      };

      utterance.onend = () => {
        if (this.visualizer) this.visualizer.setMode('idle');
        resolve();
      };

      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  }

  async toggleMic() {
    // If call is not connected, connect first
    if (this.callState !== 'connected' && this.callState !== 'escalating') {
      await this.startCall();
      await new Promise(r => setTimeout(r, 600));
    }

    if (this.recognition) {
      if (this.isRecording) {
        try {
          this.recognition.stop();
        } catch (e) {}
        this.isRecording = false;
        this.updateMicButtonUI(false);
      } else {
        try {
          this.lastSpokenText = '';
          this.recognition.start();
          this.isRecording = true;
          this.updateMicButtonUI(true);
        } catch (e) {
          console.warn('Recognition start error, restarting:', e);
          try {
            this.recognition.stop();
            setTimeout(() => {
              try {
                this.recognition.start();
                this.isRecording = true;
                this.updateMicButtonUI(true);
              } catch (e3) {}
            }, 200);
          } catch (e2) {}
        }
      }
    } else {
      const chatInput = document.getElementById('chatInput');
      if (chatInput) {
        chatInput.focus();
        chatInput.placeholder = 'Type your technical issue here and press Enter...';
      }
    }
  }

  updateMicButtonUI(recording) {
    if (!this.micToggleBtn) return;
    if (recording) {
      this.micToggleBtn.classList.add('recording');
      this.micToggleBtn.innerHTML = '🛑 Listening... (Click to Finish &amp; Send)';
    } else {
      this.micToggleBtn.classList.remove('recording');
      this.micToggleBtn.innerHTML = '🎙️ Click &amp; Speak (Microphone)';
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.btnMuteCall) {
      this.btnMuteCall.classList.toggle('active', this.isMuted);
    }
    this.appendSystemNotice(this.isMuted ? '🔇 Microphone is now Muted.' : '🔊 Microphone is now Active.');
  }

  toggleHold() {
    this.isOnHold = !this.isOnHold;
    if (this.btnHoldCall) {
      this.btnHoldCall.classList.toggle('active', this.isOnHold);
    }
    if (this.isOnHold) {
      if (this.currentAudio) this.currentAudio.pause();
      this.setStatus('Call Placed On Hold', 'thinking');
      this.appendSystemNotice('⏸️ Call is placed on hold.');
    } else {
      this.setStatus('Call Resumed', 'active');
      this.appendSystemNotice('▶️ Call resumed.');
    }
  }

  async escalateCall() {
    if (!this.sessionId) {
      await this.startCall();
      await new Promise(r => setTimeout(r, 600));
    }
    this.handleUserSpokenMessage('I need to escalate this issue to a human supervisor immediately.');
  }

  async endCall() {
    if (this.currentAudio) this.currentAudio.pause();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (this.recognition && this.isRecording) this.recognition.stop();
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
    }

    this.stopTimer();
    this.callState = 'ended';
    this.setStatus('Call Ended (Click Start Call to call again)', 'idle');
    if (this.visualizer) this.visualizer.setMode('idle');
    if (this.avatarEl) {
      this.avatarEl.classList.remove('active', 'speaking', 'escalating');
    }
    this.updateCallControlsUI();

    if (this.sessionId) {
      try {
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        formData.append('resolution', 'resolved');
        await fetch('/api/calls/end', { method: 'POST', body: formData });
      } catch (e) {
        console.error('Error ending session:', e);
      }
    }

    this.appendSystemNotice('📞 Call has ended. Thank you for calling InnoAssist Technical Support.');
    if (window.dashboardManager) window.dashboardManager.loadSessions();
  }

  startTimer() {
    this.callSeconds = 0;
    this.updateTimerDisplay();
    clearInterval(this.callTimerInterval);
    this.callTimerInterval = setInterval(() => {
      if (!this.isOnHold) {
        this.callSeconds++;
        this.updateTimerDisplay();
      }
    }, 1000);
  }

  stopTimer() {
    clearInterval(this.callTimerInterval);
  }

  updateTimerDisplay() {
    if (!this.callTimerEl) return;
    const mins = Math.floor(this.callSeconds / 60).toString().padStart(2, '0');
    const secs = (this.callSeconds % 60).toString().padStart(2, '0');
    this.callTimerEl.innerText = `${mins}:${secs}`;
  }

  setStatus(text, stateClass) {
    if (this.statusTextEl) this.statusTextEl.innerText = text;
    if (this.statusDotEl) {
      this.statusDotEl.className = 'status-dot';
      if (stateClass) this.statusDotEl.classList.add(stateClass);
    }
  }

  updateCallControlsUI() {
    const isCallActive = this.callState === 'connected' || this.callState === 'escalating';
    if (this.btnStartCall) this.btnStartCall.style.display = isCallActive ? 'none' : 'flex';
    if (this.btnEndCall) this.btnEndCall.style.display = isCallActive ? 'flex' : 'none';
  }

  appendTranscriptBubble(role, text, latency = {}, intent = '') {
    if (!this.transcriptFeedEl) return;
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    let metaHtml = `<div class="bubble-footer"><span>${role === 'assistant' ? '🤖 Maanu (AI Support)' : '👤 Caller'} &bull; ${now}</span>`;
    if (role === 'assistant' && latency && latency.llm_ms) {
      metaHtml += `<span>⚡ ${Math.round(latency.llm_ms)}ms</span>`;
    }
    metaHtml += `</div>`;

    bubble.innerHTML = `<div>${text}</div>${metaHtml}`;
    this.transcriptFeedEl.appendChild(bubble);
    this.transcriptFeedEl.scrollTop = this.transcriptFeedEl.scrollHeight;
  }

  appendSystemNotice(text) {
    if (!this.transcriptFeedEl) return;
    const notice = document.createElement('div');
    notice.className = 'chat-bubble system';
    notice.innerText = text;
    this.transcriptFeedEl.appendChild(notice);
    this.transcriptFeedEl.scrollTop = this.transcriptFeedEl.scrollHeight;
  }
}

window.PhoneCallManager = PhoneCallManager;
