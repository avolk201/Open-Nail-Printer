<script setup>
import { ref } from 'vue';
import { UploadCloud, Image as ImageIcon, Send } from 'lucide-vue-next';

const file = ref(null);
const previewUrl = ref(null);
const isUploading = ref(false);

const handleFileUpload = (event) => {
  const selectedFile = event.target.files[0];
  if (selectedFile) {
    file.value = selectedFile;
    previewUrl.value = URL.createObjectURL(selectedFile);
  }
};

const triggerUpload = () => {
  document.getElementById('file-upload').click();
};

const submitImage = async () => {
  if (!file.value) return;
  isUploading.value = true;
  
  // Simulate API call
  setTimeout(() => {
    isUploading.value = false;
    alert('Image successfully sent to printer!');
  }, 1500);
};
</script>

<template>
  <div class="mobile-container">
    <header class="header">
      <h2>Upload Design</h2>
      <p>Select an image to print on your nail</p>
    </header>

    <main class="content">
      <div 
        class="upload-area glass-panel" 
        :class="{ 'has-image': previewUrl }"
        @click="!previewUrl && triggerUpload()"
      >
        <input 
          type="file" 
          id="file-upload" 
          accept="image/*" 
          @change="handleFileUpload" 
          hidden
        />
        
        <template v-if="!previewUrl">
          <UploadCloud :size="64" color="#8b5cf6" />
          <h3>Tap to select image</h3>
          <p>JPEG, PNG up to 10MB</p>
        </template>
        
        <template v-else>
          <div class="preview-container">
            <!-- Simulated Nail Mask -->
            <div class="nail-mask">
              <img :src="previewUrl" class="preview-image" />
            </div>
            <button class="reselect-btn glass-panel" @click.stop="triggerUpload">
              <ImageIcon :size="18" /> Change Image
            </button>
          </div>
        </template>
      </div>

      <button 
        class="btn primary submit-btn" 
        :disabled="!previewUrl || isUploading"
        @click="submitImage"
      >
        <Send v-if="!isUploading" :size="20" />
        <span class="loader" v-else></span>
        {{ isUploading ? 'Sending...' : 'Send to Printer' }}
      </button>
    </main>
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
}

.header {
  text-align: center;
  margin-bottom: 2rem;
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
</style>
