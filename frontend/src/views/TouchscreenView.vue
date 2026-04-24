<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { Camera, RefreshCw, Printer, XCircle, UploadCloud, CheckCircle, Image as ImageIcon } from 'lucide-vue-next';
import { useRouter } from 'vue-router';

const router = useRouter();
const status = ref('Idle');
const streamImg = ref(null);
const frozenCanvas = ref(null);
const boundingBox = ref(null);

const isAligningUI = ref(false);
const isAdjustingUI = ref(false);
const isDrawing = ref(false);
const drawStart = ref({x: 0, y: 0});
const drawEnd = ref({x: 0, y: 0});

const transformScale = ref(1.0);
const transformRotation = ref(0);
const transformXOffset = ref(0);
const transformYOffset = ref(0);

const activeType = ref('single');
const activeSet = ref(null);
const singleDesignUrl = ref('');
const FINGERS = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'];
const currentFingerIndex = ref(0);

const currentFingerUrl = computed(() => {
  if (activeType.value === 'single') return singleDesignUrl.value;
  if (activeType.value === 'set' && activeSet.value) {
    const fingerName = FINGERS[currentFingerIndex.value];
    const filename = activeSet.value.fingers[fingerName];
    return `/uploads/${filename}`;
  }
  return '';
});

const hasDesign = computed(() => !!currentFingerUrl.value);
const mountTime = ref(Date.now());

const handleDesignError = (e) => {
  // Silent error, handle if needed
};

const fetchActiveDesign = async () => {
  try {
    const res = await fetch('/api/designs/active');
    const data = await res.json();
    activeType.value = data.type;
    if (data.type === 'single') {
      singleDesignUrl.value = data.url;
      activeSet.value = null;
    } else if (data.type === 'set') {
      activeSet.value = data.set;
      singleDesignUrl.value = '';
    }
  } catch(e) {
    console.error("Failed to fetch active design", e);
  }
};

const drawingBox = computed(() => {
  const left = Math.min(drawStart.value.x, drawEnd.value.x);
  const top = Math.min(drawStart.value.y, drawEnd.value.y);
  const width = Math.abs(drawStart.value.x - drawEnd.value.x);
  const height = Math.abs(drawStart.value.y - drawEnd.value.y);
  
  if (width === 0 && height === 0) return null;
  return { left, top, width, height };
});

const bboxStyle = computed(() => {
  const box = isAligningUI.value ? drawingBox.value : boundingBox.value;
  if (!box) return {};
  return {
    left: `${box.left}px`,
    top: `${box.top}px`,
    width: `${box.width}px`,
    height: `${box.height}px`,
  };
});

const transformStyle = computed(() => {
  return {
    transform: `translate(${transformXOffset.value}px, ${transformYOffset.value}px) rotate(${transformRotation.value}deg) scale(${transformScale.value})`
  };
});

const getPointerPos = (e, container) => {
  const rect = container.getBoundingClientRect();
  const clientX = e.touches ? e.touches[0].clientX : e.clientX;
  const clientY = e.touches ? e.touches[0].clientY : e.clientY;
  return {
    x: clientX - rect.left,
    y: clientY - rect.top
  };
};

const startDrawing = (e) => {
  if (!isAligningUI.value) return;
  isDrawing.value = true;
  const pos = getPointerPos(e, e.currentTarget);
  drawStart.value = pos;
  drawEnd.value = pos;
};

const draw = (e) => {
  if (!isDrawing.value) return;
  const pos = getPointerPos(e, e.currentTarget);
  drawEnd.value = pos;
};

const stopDrawing = () => {
  isDrawing.value = false;
};

const confirmAlignment = async () => {
  if (!drawingBox.value) {
    alert("Please draw a bounding box first.");
    return;
  }
  
  const box = drawingBox.value;
  
  // Map CSS coordinates to native video coordinates
  const vw = frozenCanvas.value.width;
  const vh = frozenCanvas.value.height;
  const cw = frozenCanvas.value.clientWidth;
  const ch = frozenCanvas.value.clientHeight;
  
  const videoRatio = vw / vh;
  const containerRatio = cw / ch;

  let renderWidth, renderHeight, xOffset = 0, yOffset = 0;

  if (containerRatio > videoRatio) {
    renderHeight = ch;
    renderWidth = ch * videoRatio;
    xOffset = (cw - renderWidth) / 2;
  } else {
    renderWidth = cw;
    renderHeight = cw / videoRatio;
    yOffset = (ch - renderHeight) / 2;
  }

  const scale = vw / renderWidth;

  const nativeBBox = {
    x: Math.round((box.left - xOffset) * scale),
    y: Math.round((box.top - yOffset) * scale),
    w: Math.round(box.width * scale),
    h: Math.round(box.height * scale)
  };

  try {
    const response = await fetch('/api/align', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nativeBBox)
    });

    if (response.ok) {
      console.log("Alignment confirmed!");
      boundingBox.value = box;
      isAligningUI.value = false;
    } else {
      alert("Failed to save alignment.");
    }
  } catch (err) {
    console.error("Error saving alignment:", err);
    alert("Error connecting to printer.");
  }
};

const handleAction = async (action) => {
  status.value = action;
  console.log(`Action triggered: ${action}`);
  
  if (action === 'Idle') {
    isAligningUI.value = false;
    boundingBox.value = null;
    drawStart.value = {x: 0, y: 0};
    drawEnd.value = {x: 0, y: 0};
    return;
  }

  if (action === 'Aligning') {
    if (streamImg.value && frozenCanvas.value) {
      frozenCanvas.value.width = streamImg.value.naturalWidth || 640;
      frozenCanvas.value.height = streamImg.value.naturalHeight || 480;
      const ctx = frozenCanvas.value.getContext('2d');
      ctx.drawImage(streamImg.value, 0, 0, frozenCanvas.value.width, frozenCanvas.value.height);
    }
    isAligningUI.value = true;
    return; // Wait for user to draw and confirm
  }

  if (action === 'Adjusting') {
    isAdjustingUI.value = true;
    return;
  }

  try {
    let response;
    let endpoint = '';
    
    if (action === 'Homing') {
      endpoint = '/api/home';
      response = await fetch(endpoint, { method: 'POST' });
    }
    else if (action === 'Printing') {
      endpoint = '/api/print';
      const filePath = currentFingerUrl.value ? currentFingerUrl.value.replace(/^\//, '') : undefined;
      
      response = await fetch(endpoint, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: filePath,
          transform: {
            scale: transformScale.value,
            rotation: transformRotation.value,
            x_offset: transformXOffset.value,
            y_offset: transformYOffset.value
          }
        })
      });
    }

    if (response) {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        alert(`Error during ${action}: ${errorData.detail || response.statusText}`);
        status.value = 'Idle'; 
      } else {
        if (action === 'Printing' && activeType.value === 'set') {
          // Advance to next finger
          if (currentFingerIndex.value < FINGERS.length - 1) {
            currentFingerIndex.value++;
            status.value = 'Idle';
            isAligningUI.value = false;
            boundingBox.value = null; // Reset bounding box for next finger
            alert(`Print successful! Please insert your ${FINGERS[currentFingerIndex.value]} finger.`);
          } else {
            alert('Set Complete! All 5 fingers printed successfully.');
            status.value = 'Idle';
            currentFingerIndex.value = 0;
            activeSet.value = null;
            activeType.value = 'single';
          }
        }
      }
    }
  } catch (error) {
    console.error(`Error communicating with backend during ${action}:`, error);
    alert(`Failed to connect to printer for ${action}. Is the backend running?`);
    status.value = 'Idle';
  }
};

onMounted(() => {
  mountTime.value = Date.now();
  fetchActiveDesign();
});

onUnmounted(() => {
  // Nothing to cleanup for streamImg
});
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
      <div 
        class="video-feed glass-panel"
        @mousedown="startDrawing"
        @mousemove="draw"
        @mouseup="stopDrawing"
        @mouseleave="stopDrawing"
        @touchstart.prevent="startDrawing"
        @touchmove.prevent="draw"
        @touchend.prevent="stopDrawing"
        :class="{ 'is-aligning': isAligningUI }"
      >
        <div v-if="activeType === 'set'" class="finger-banner">
           Current Finger: <span class="finger-highlight">{{ FINGERS[currentFingerIndex] }}</span>
        </div>
        <img ref="streamImg" :src="'/api/stream'" class="live-feed" v-show="!isAligningUI" crossorigin="anonymous" />
        <canvas ref="frozenCanvas" class="live-feed" v-show="isAligningUI"></canvas>
        
        <div class="overlay-container" v-if="boundingBox && !isAligningUI" :style="bboxStyle">
          <img 
            v-if="hasDesign" 
            :src="`${currentFingerUrl}?t=${mountTime}`" 
            class="design-overlay" 
            :style="transformStyle"
            @error="handleDesignError"
          />
        </div>

        <div v-if="bboxStyle.width" class="bounding-box" :style="bboxStyle"></div>
        <div class="crosshair" v-if="!bboxStyle.width && !isAligningUI"></div>
        <div class="align-overlay-message" v-if="isAligningUI">
          Drag to draw bounding box
        </div>
      </div>

      <div class="controls">
        <template v-if="isAligningUI">
          <button class="btn success" @click="confirmAlignment">
            <CheckCircle :size="24" />
            Confirm
          </button>
          <button class="btn danger" @click="handleAction('Idle')">
            <XCircle :size="24" />
            Cancel
          </button>
        </template>
        <template v-else-if="isAdjustingUI">
          <div class="sliders-panel glass-panel">
             <div class="slider-row">
               <label>Zoom ({{transformScale}}x)</label>
               <input type="range" min="0.5" max="3.0" step="0.1" v-model.number="transformScale">
             </div>
             <div class="slider-row">
               <label>Rotate ({{transformRotation}}°)</label>
               <input type="range" min="-180" max="180" step="5" v-model.number="transformRotation">
             </div>
             <div class="slider-row">
               <label>Pan X</label>
               <input type="range" min="-300" max="300" step="10" v-model.number="transformXOffset">
             </div>
             <div class="slider-row">
               <label>Pan Y</label>
               <input type="range" min="-300" max="300" step="10" v-model.number="transformYOffset">
             </div>
          </div>
          <button class="btn success" @click="isAdjustingUI = false">
            <CheckCircle :size="24" /> Done Adjusting
          </button>
        </template>
        <template v-else>
          <button class="btn warning" @click="handleAction('Homing')">
            <RefreshCw :size="24" />
            Ready (Home)
          </button>
          <button class="btn" style="background-color: #4f46e5;" @click="router.push('/gallery')">
            <ImageIcon :size="24" />
            Designs Gallery
          </button>
          <div style="display:flex; gap:0.5rem;">
            <button class="btn primary" style="flex:1" @click="handleAction('Aligning')">
              <Camera :size="24" /> Align
            </button>
            <button class="btn secondary" style="flex:1; background: #3b82f6;" :disabled="!boundingBox || !hasDesign" @click="handleAction('Adjusting')">
              Adjust
            </button>
          </div>
          <div style="display:flex; gap:0.5rem;" v-if="activeType === 'set'">
            <button class="btn success" style="flex:2" @click="handleAction('Printing')">
              <Printer :size="24" /> Print
            </button>
            <button class="btn warning" style="flex:1" @click="currentFingerIndex++">
              Skip
            </button>
          </div>
          <button v-else class="btn success" @click="handleAction('Printing')">
            <Printer :size="24" />
            Print
          </button>
          <button class="btn danger" @click="handleAction('Idle')">
            <XCircle :size="24" />
            Cancel
          </button>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.touchscreen-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: 1rem;
  gap: 1rem;
  background: linear-gradient(135deg, #0f172a, #020617);
  box-sizing: border-box;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
}

.header h1 {
  font-size: 1.6rem;
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
  gap: 1rem;
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

.live-feed {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain; /* ensures whole feed is visible and coordinate mapping is accurate */
  z-index: 1;
  pointer-events: none;
}

.video-feed.is-aligning {
  cursor: crosshair;
}

.align-overlay-message {
  position: absolute;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  font-weight: 600;
  z-index: 30;
  pointer-events: none;
}

.finger-banner {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(139, 92, 246, 0.9);
  color: white;
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 1.2rem;
  z-index: 30;
  pointer-events: none;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.finger-highlight {
  color: #fbbf24;
  font-weight: 800;
}

.bounding-box {
  position: absolute;
  border: 3px solid #10b981;
  background-color: rgba(16, 185, 129, 0.2);
  z-index: 20;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
  transition: all 0.2s ease-in-out;
}

.overlay-container {
  position: absolute;
  z-index: 25;
  overflow: hidden;
  border-radius: 40px 40px 20px 20px; /* roughly nail shaped */
  pointer-events: none;
}

.design-overlay {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.8;
  transform-origin: center center;
}

.sliders-panel {
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  flex: 4;
  padding: 0.5rem 1rem;
}

.slider-row {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.slider-row label {
  font-size: 0.9rem;
  color: #9ca3af;
}

.slider-row input[type=range] {
  width: 100%;
  accent-color: #8b5cf6;
}

.crosshair {
  position: absolute;
  width: 100px;
  height: 100px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50px;
  z-index: 10;
}

.controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.controls .btn {
  flex: 1;
  font-size: 1.2rem;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
}
</style>
