<script setup>
import { ref } from 'vue';
import { Camera, RefreshCw, Printer, XCircle } from 'lucide-vue-next';

const status = ref('Idle');

const handleAction = (action) => {
  status.value = action;
  console.log(`Action triggered: ${action}`);
  // In a real implementation, this would call FastAPI endpoints
};
</script>

<template>
  <div class="touchscreen-container">
    <header class="header glass-panel">
      <h1>Nail Gel Printer</h1>
      <div class="status-badge" :class="status.toLowerCase()">
        {{ status }}
      </div>
    </header>

    <main class="main-content">
      <div class="video-feed glass-panel">
        <div class="crosshair"></div>
        <div class="camera-placeholder">
          <Camera :size="48" color="#6b7280" />
          <p>Live View Connecting...</p>
        </div>
      </div>

      <div class="controls">
        <button class="btn warning" @click="handleAction('Homing')">
          <RefreshCw :size="24" />
          Ready (Home)
        </button>
        <button class="btn primary" @click="handleAction('Aligning')">
          <Camera :size="24" />
          Align
        </button>
        <button class="btn success" @click="handleAction('Printing')">
          <Printer :size="24" />
          Print
        </button>
        <button class="btn danger" @click="handleAction('Idle')">
          <XCircle :size="24" />
          Cancel
        </button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.touchscreen-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1.5rem;
  gap: 1.5rem;
  background: linear-gradient(135deg, #0f172a, #020617);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
}

.header h1 {
  font-size: 1.8rem;
  font-weight: 700;
  background: linear-gradient(to right, #a78bfa, #f472b6);
  -webkit-background-clip: text;
  color: transparent;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-weight: 600;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--surface-border);
}

.status-badge.printing { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.status-badge.aligning { background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
.status-badge.homing { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

.main-content {
  display: flex;
  flex: 1;
  gap: 1.5rem;
  min-height: 0;
}

.video-feed {
  flex: 3;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.crosshair {
  position: absolute;
  width: 100px;
  height: 100px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  z-index: 10;
}

.crosshair::before, .crosshair::after {
  content: '';
  position: absolute;
  background: rgba(255, 255, 255, 0.5);
}

.crosshair::before { top: -10px; bottom: -10px; left: 49px; width: 2px; }
.crosshair::after { left: -10px; right: -10px; top: 49px; height: 2px; }

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: #6b7280;
}

.controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.controls .btn {
  flex: 1;
  font-size: 1.4rem;
  border-radius: 20px;
}
</style>
