/**
 * Audio Visualizer Module for Canvas Waveform Rendering
 */
class AudioVisualizer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.isActive = false;
    this.isSpeaking = false;
    this.mode = 'idle'; // 'idle', 'listening', 'speaking', 'thinking', 'escalating'
    this.phase = 0;
    this.animationFrame = null;
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    this.startLoop();
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    this.canvas.width = this.canvas.parentElement.clientWidth || 300;
    this.canvas.height = 60;
  }

  setMode(mode) {
    this.mode = mode;
  }

  startLoop() {
    const draw = () => {
      this.draw();
      this.animationFrame = requestAnimationFrame(draw);
    };
    draw();
  }

  draw() {
    if (!this.ctx || !this.canvas) return;
    const width = this.canvas.width;
    const height = this.canvas.height;
    this.ctx.clearRect(0, 0, width, height);

    this.phase += 0.05;

    let strokeColor = '#475569';
    let amplitude = 5;
    let waveCount = 2;

    if (this.mode === 'speaking') {
      strokeColor = '#0284c7';
      amplitude = 18;
      waveCount = 3;
    } else if (this.mode === 'listening') {
      strokeColor = '#10b981';
      amplitude = 15;
      waveCount = 2;
    } else if (this.mode === 'thinking') {
      strokeColor = '#f59e0b';
      amplitude = 9;
      waveCount = 2;
    } else if (this.mode === 'escalating') {
      strokeColor = '#ef4444';
      amplitude = 22;
      waveCount = 4;
    }

    // Draw multi-layer smooth sine waves
    for (let i = 0; i < waveCount; i++) {
      this.ctx.beginPath();
      this.ctx.lineWidth = i === 0 ? 2.5 : 1.5;
      this.ctx.strokeStyle = i === 0 ? strokeColor : `${strokeColor}55`;

      const offsetPhase = this.phase + (i * 0.8);
      const waveAmp = amplitude * (1 - (i * 0.25));

      for (let x = 0; x < width; x++) {
        const normX = (x / width) * 2 - 1;
        const windowFactor = Math.exp(-3 * normX * normX);
        const y = (height / 2) + Math.sin(x * 0.04 + offsetPhase) * waveAmp * windowFactor;
        if (x === 0) {
          this.ctx.moveTo(x, y);
        } else {
          this.ctx.lineTo(x, y);
        }
      }
      this.ctx.stroke();
    }
  }
}

window.AudioVisualizer = AudioVisualizer;
