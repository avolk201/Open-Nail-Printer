<script setup>
import { ref, computed } from 'vue';
import { UploadCloud, Image as ImageIcon, Send, ArrowLeft } from 'lucide-vue-next';
import { useRouter } from 'vue-router';

const router = useRouter();
const uploadMode = ref('single'); // 'single' or 'set'
const setName = ref('');

// Single mode state
const singleFile = ref(null);
const singlePreviewUrl = ref(null);

// Set mode state
const setFiles = ref({
  Thumb: null,
  Index: null,
  Middle: null,
  Ring: null,
  Pinky: null
});
const setPreviewUrls = ref({
  Thumb: null,
  Index: null,
  Middle: null,
  Ring: null,
  Pinky: null
});

const isUploading = ref(false);

// Adjuster state
const adjustingFinger = ref(null);
const adjustingOriginalFileUrl = ref(null);
const transformScale = ref(1);
const transformRotation = ref(0);
const transformX = ref(0);
const transformY = ref(0);

const adjustTransformStyle = computed(() => {
  return {
    transform: `translate(${transformX.value}px, ${transformY.value}px) rotate(${transformRotation.value}deg) scale(${transformScale.value})`
  }
});

const handleFileUpload = (event, finger = null) => {
  const selectedFile = event.target.files[0];
  if (selectedFile) {
    adjustingFinger.value = finger || 'single';
    adjustingOriginalFileUrl.value = URL.createObjectURL(selectedFile);
    
    transformScale.value = 1;
    transformRotation.value = 0;
    transformX.value = 0;
    transformY.value = 0;
    
    // Clear the input so selecting the same file again works
    event.target.value = '';
  }
};

const triggerUpload = (finger = null) => {
  const id = finger ? `file-upload-${finger}` : 'file-upload-single';
  document.getElementById(id).click();
};

const cancelAdjust = () => {
  adjustingOriginalFileUrl.value = null;
  adjustingFinger.value = null;
};

const saveCrop = async () => {
  const img = new Image();
  img.src = adjustingOriginalFileUrl.value;
  await new Promise(r => img.onload = r);
  
  const canvas = document.createElement('canvas');
  canvas.width = 180;
  canvas.height = 250;
  const ctx = canvas.getContext('2d');
  
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, 180, 250);
  
  const cx = 180 / 2;
  const cy = 250 / 2;
  const ix = img.width / 2;
  const iy = img.height / 2;
  
  const scaleX = 180 / img.width;
  const scaleY = 250 / img.height;
  const baseScale = Math.max(scaleX, scaleY);
  
  ctx.translate(cx, cy);
  ctx.translate(transformX.value, transformY.value);
  ctx.rotate(transformRotation.value * Math.PI / 180);
  ctx.scale(baseScale * transformScale.value, baseScale * transformScale.value);
  ctx.translate(-ix, -iy);
  
  ctx.drawImage(img, 0, 0);
  
  canvas.toBlob((blob) => {
    const croppedFile = new File([blob], `cropped_${Date.now()}.png`, { type: 'image/png' });
    const url = URL.createObjectURL(croppedFile);
    
    if (adjustingFinger.value === 'single') {
      singleFile.value = croppedFile;
      singlePreviewUrl.value = url;
    } else {
      setFiles.value[adjustingFinger.value] = croppedFile;
      setPreviewUrls.value[adjustingFinger.value] = url;
    }
    
    adjustingOriginalFileUrl.value = null;
  }, 'image/png');
};

const uploadFileToBackend = async (fileToUpload) => {
  const formData = new FormData();
  formData.append('file', fileToUpload);
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Failed to upload file');
  const data = await response.json();
  // We need just the filename, not the full path like 'uploads/file.png'
  return data.file_path.split('/').pop();
};

const submitImage = async () => {
  if (uploadMode.value === 'single' && !singleFile.value) return;
  if (uploadMode.value === 'set' && (!setName.value || !Object.values(setFiles.value).every(f => f))) {
    alert('Please provide a set name and an image for all 5 fingers.');
    return;
  }
  
  isUploading.value = true;
  
  try {
    if (uploadMode.value === 'single') {
      await uploadFileToBackend(singleFile.value);
      alert('Image successfully sent to printer!');
    } else {
      const fingers = {};
      for (const finger of Object.keys(setFiles.value)) {
        const filename = await uploadFileToBackend(setFiles.value[finger]);
        fingers[finger] = filename;
      }
      
      const setResponse = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: setName.value,
          fingers: fingers
        })
      });
      
      if (!setResponse.ok) throw new Error('Failed to save set');
      alert('Design Set successfully sent to printer!');
    }
    
    router.push('/');
  } catch (error) {
    console.error('Upload error:', error);
    alert('Failed to connect to printer.');
  } finally {
    isUploading.value = false;
  }
};
</script>

<template>
  <div class="mobile-container">
    <div v-if="adjustingOriginalFileUrl" class="adjuster-modal glass-panel">
      <h2>Adjust Design</h2>
      
      <div class="preview-container">
        <div class="nail-mask">
          <img :src="adjustingOriginalFileUrl" class="adjust-preview" :style="adjustTransformStyle" />
        </div>
      </div>

      <div class="sliders">
        <div class="slider-group">
          <label>Scale</label>
          <input type="range" v-model.number="transformScale" min="0.5" max="3" step="0.05" />
        </div>
        <div class="slider-group">
          <label>Rotation</label>
          <input type="range" v-model.number="transformRotation" min="-180" max="180" step="1" />
        </div>
        <div class="slider-group">
          <label>X Offset</label>
          <input type="range" v-model.number="transformX" min="-150" max="150" step="1" />
        </div>
        <div class="slider-group">
          <label>Y Offset</label>
          <input type="range" v-model.number="transformY" min="-150" max="150" step="1" />
        </div>
      </div>

      <div style="display:flex; gap:1rem; width:100%; margin-top:1rem;">
        <button class="btn danger" style="flex:1" @click="cancelAdjust">Cancel</button>
        <button class="btn success" style="flex:2" @click="saveCrop">Save Crop</button>
      </div>
    </div>

    <template v-else>
      <header class="header">
      <div class="header-top">
        <button class="back-btn glass-panel" @click="router.push('/')">
          <ArrowLeft :size="24" />
        </button>
        <h2>Upload Design</h2>
      </div>
      <p>Send an image or a full set to your nail printer</p>
      
      <div class="mode-toggle">
        <button 
          :class="['toggle-btn', { active: uploadMode === 'single' }]" 
          @click="uploadMode = 'single'"
        >Single</button>
        <button 
          :class="['toggle-btn', { active: uploadMode === 'set' }]" 
          @click="uploadMode = 'set'"
        >Full Hand Set</button>
      </div>
    </header>

    <main class="content">
      <template v-if="uploadMode === 'single'">
        <div 
          class="upload-area glass-panel" 
          :class="{ 'has-image': singlePreviewUrl }"
          @click="!singlePreviewUrl && triggerUpload()"
        >
          <input 
            type="file" 
            id="file-upload-single" 
            accept="image/*" 
            @change="e => handleFileUpload(e, null)" 
            hidden
          />
          
          <template v-if="!singlePreviewUrl">
            <UploadCloud :size="64" color="#8b5cf6" />
            <h3>Tap to select image</h3>
            <p>JPEG, PNG up to 10MB</p>
          </template>
          
          <template v-else>
            <div class="preview-container">
              <!-- Simulated Nail Mask -->
              <div class="nail-mask">
                <img :src="singlePreviewUrl" class="preview-image" />
              </div>
              <button class="reselect-btn glass-panel" @click.stop="triggerUpload()">
                <ImageIcon :size="18" /> Change Image
              </button>
            </div>
          </template>
        </div>
      </template>

      <template v-else>
        <div class="set-name-input">
          <label>Set Name:</label>
          <input type="text" v-model="setName" placeholder="e.g. Summer Vibes" />
        </div>
        
        <div class="fingers-grid">
          <div 
            v-for="finger in ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']" 
            :key="finger"
            class="finger-upload-slot glass-panel"
            @click="!setPreviewUrls[finger] && triggerUpload(finger)"
          >
            <input 
              type="file" 
              :id="`file-upload-${finger}`" 
              accept="image/*" 
              @change="e => handleFileUpload(e, finger)" 
              hidden
            />
            <div class="finger-label">{{ finger }}</div>
            
            <template v-if="!setPreviewUrls[finger]">
              <UploadCloud :size="24" color="#8b5cf6" />
            </template>
            <template v-else>
              <img :src="setPreviewUrls[finger]" class="mini-preview" />
              <button class="mini-reselect" @click.stop="triggerUpload(finger)">
                <ImageIcon :size="14" />
              </button>
            </template>
          </div>
        </div>
      </template>

      <button 
        class="btn primary submit-btn" 
        :disabled="isUploading"
        @click="submitImage"
      >
        <Send v-if="!isUploading" :size="20" />
        <span class="loader" v-else></span>
        {{ isUploading ? 'Sending...' : 'Send to Printer' }}
      </button>
    </main>
    </template>
  </div>
</template>

<style scoped>
.mobile-container {
  max-width: 600px;
  margin: 0 auto;
  min-height: 100vh;
  padding: 2rem 1.5rem;
  display: flex;
  flex-direction: column;
  position: relative;
}

.header {
  text-align: center;
  margin-bottom: 2rem;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-bottom: 0.5rem;
}

.back-btn {
  position: absolute;
  left: 0;
  border: none;
  color: white;
  padding: 0.5rem;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header h2 {
  font-size: 2rem;
  font-weight: 800;
  margin-bottom: 0.5rem;
  background: linear-gradient(to right, #a78bfa, #f472b6);
  -webkit-background-clip: text;
  color: transparent;
}

.header p {
  color: #9ca3af;
  margin-bottom: 1rem;
}

.mode-toggle {
  display: flex;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 4px;
  max-width: 300px;
  margin: 0 auto;
}

.toggle-btn {
  flex: 1;
  background: transparent;
  border: none;
  color: #9ca3af;
  padding: 0.5rem 1rem;
  border-radius: 999px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: #8b5cf6;
  color: white;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.upload-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  border: 2px dashed rgba(139, 92, 246, 0.4);
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 400px;
  position: relative;
}

.upload-area:not(.has-image):hover {
  background: rgba(139, 92, 246, 0.1);
  border-color: #8b5cf6;
}

.upload-area h3 {
  font-size: 1.2rem;
  font-weight: 600;
  color: #e5e7eb;
}

.upload-area p {
  font-size: 0.9rem;
  color: #6b7280;
}

.preview-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 1.5rem;
}

.nail-mask {
  width: 180px;
  height: 250px;
  border-radius: 90px 90px 40px 40px; /* Rough nail shape */
  overflow: hidden;
  box-shadow: 0 0 0 4px #8b5cf6, 0 20px 25px -5px rgba(0, 0, 0, 0.5);
  background: #000;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.reselect-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 9999px;
  border: none;
  color: white;
  font-weight: 600;
  cursor: pointer;
  z-index: 10;
}

.reselect-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.submit-btn {
  width: 100%;
  padding: 1.5rem;
  border-radius: 100px;
  font-size: 1.2rem;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loader {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.set-name-input {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.set-name-input label {
  font-weight: 600;
  color: #e5e7eb;
}

.set-name-input input {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  padding: 1rem;
  border-radius: 12px;
  font-size: 1rem;
}

.fingers-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: center;
}

.finger-upload-slot {
  width: calc(33% - 1rem);
  aspect-ratio: 3 / 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(139, 92, 246, 0.4);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.2s;
}

.finger-upload-slot:hover {
  border-color: #8b5cf6;
  background: rgba(139, 92, 246, 0.1);
}

.finger-label {
  position: absolute;
  top: 5px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  z-index: 10;
}

.mini-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.mini-reselect {
  position: absolute;
  bottom: 5px;
  right: 5px;
  background: rgba(0,0,0,0.6);
  border: none;
  border-radius: 50%;
  padding: 5px;
  color: white;
  cursor: pointer;
}

.adjuster-modal {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  background: #0f0f13; /* solid bg to hide content */
}

.adjuster-modal h2 {
  margin-bottom: 2rem;
  color: white;
}

.adjust-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform-origin: center center;
}

.sliders {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-top: 2rem;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.slider-group label {
  font-weight: 600;
  color: #e5e7eb;
}

.slider-group input[type="range"] {
  width: 100%;
  accent-color: #8b5cf6;
}
</style>
