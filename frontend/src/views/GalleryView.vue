<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeft, Image as ImageIcon, Phone } from 'lucide-vue-next';

const router = useRouter();
const designs = ref([]);
const sets = ref([]);
const viewMode = ref('single'); // 'single' or 'set'
const uploadUrl = ref('');
const qrUrl = ref('');

const itemsPerPage = 12;
const currentDesignPage = ref(1);
const currentSetPage = ref(1);

const totalDesignPages = computed(() => Math.ceil(designs.value.length / itemsPerPage) || 1);
const paginatedDesigns = computed(() => {
  const start = (currentDesignPage.value - 1) * itemsPerPage;
  return designs.value.slice(start, start + itemsPerPage);
});

const totalSetPages = computed(() => Math.ceil(sets.value.length / itemsPerPage) || 1);
const paginatedSets = computed(() => {
  const start = (currentSetPage.value - 1) * itemsPerPage;
  return sets.value.slice(start, start + itemsPerPage);
});

const fetchDesigns = async () => {
  try {
    const res = await fetch('/api/designs');
    designs.value = await res.json();
    
    const setsRes = await fetch('/api/sets');
    sets.value = await setsRes.json();
  } catch (e) {
    console.error("Failed to fetch data", e);
  }
};

const selectDesign = async (filename) => {
  try {
    await fetch('/api/designs/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'single', filename })
    });
    router.push('/');
  } catch (e) {
    console.error("Failed to select design", e);
  }
};

const selectSet = async (setObj) => {
  try {
    await fetch('/api/designs/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'set', set_data: setObj })
    });
    router.push('/');
  } catch (e) {
    console.error("Failed to select set", e);
  }
};

const fetchUploadUrl = async () => {
  try {
    const res = await fetch('/api/system/ip');
    const data = await res.json();
    const port = window.location.port ? `:${window.location.port}` : '';
    uploadUrl.value = `http://${data.ip}${port}/upload`;
  } catch (e) {
    console.error("Failed to fetch IP", e);
    uploadUrl.value = `${window.location.protocol}//${window.location.host}/upload`;
  }
  qrUrl.value = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(uploadUrl.value)}`;
};

onMounted(() => {
  fetchDesigns();
  fetchUploadUrl();
});
</script>

<template>
  <div class="gallery-container">
    <header class="header glass-panel">
      <div style="display: flex; align-items: center; gap: 1rem;">
        <button class="icon-btn" @click="router.push('/')">
          <ArrowLeft :size="24" />
        </button>
        <h1>Designs Gallery</h1>
      </div>
    </header>

    <div class="content">
      <div class="grid-section glass-panel">
        <div class="section-header">
          <h2 style="display: flex; align-items: center; gap: 0.5rem;"><ImageIcon /> Select to Print</h2>
          <div class="mode-toggle">
            <button :class="['toggle-btn', { active: viewMode === 'single' }]" @click="viewMode = 'single'">Single Designs</button>
            <button :class="['toggle-btn', { active: viewMode === 'set' }]" @click="viewMode = 'set'">Full Hand Sets</button>
          </div>
        </div>

        <div class="grid-container" v-if="viewMode === 'single'">
          <div class="grid">
            <div 
              v-for="design in paginatedDesigns" 
              :key="design.filename" 
              class="grid-item"
              @click="selectDesign(design.filename)"
            >
              <img :src="design.url" />
            </div>
            <div v-if="designs.length === 0" style="padding: 2rem; color: #9ca3af;">
              No designs uploaded yet.
            </div>
          </div>
          <div class="pagination" v-if="designs.length > 0">
            <button class="page-btn" :disabled="currentDesignPage === 1" @click="currentDesignPage--">Previous</button>
            <span>Page {{ currentDesignPage }} of {{ totalDesignPages }}</span>
            <button class="page-btn" :disabled="currentDesignPage === totalDesignPages" @click="currentDesignPage++">Next</button>
          </div>
        </div>

        <div class="grid-container" v-if="viewMode === 'set'">
          <div class="grid">
            <div 
              v-for="setObj in paginatedSets" 
              :key="setObj.name" 
              class="grid-item set-item"
              @click="selectSet(setObj)"
            >
              <div class="set-preview">
                 <img :src="`/uploads/${setObj.fingers.Thumb}`" />
                 <img :src="`/uploads/${setObj.fingers.Index}`" />
              </div>
              <div class="set-name">{{ setObj.name }}</div>
            </div>
            <div v-if="sets.length === 0" style="padding: 2rem; color: #9ca3af;">
              No sets uploaded yet.
            </div>
          </div>
          <div class="pagination" v-if="sets.length > 0">
            <button class="page-btn" :disabled="currentSetPage === 1" @click="currentSetPage--">Previous</button>
            <span>Page {{ currentSetPage }} of {{ totalSetPages }}</span>
            <button class="page-btn" :disabled="currentSetPage === totalSetPages" @click="currentSetPage++">Next</button>
          </div>
        </div>
      </div>

      <div class="upload-section glass-panel">
        <h2 style="margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;"><Phone /> Upload from Phone</h2>
        <p style="margin-bottom: 1rem; color: #9ca3af; font-size: 0.9rem;">
          Scan this QR code with your phone to upload a new design.
        </p>
        <div class="qr-container">
          <img v-if="qrUrl" :src="qrUrl" alt="QR Code" />
        </div>
        <p style="margin-top: 1rem; font-size: 0.8rem; word-break: break-all; color: #6b7280;">
          {{ uploadUrl }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gallery-container {
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
  padding: 0.5rem 1rem;
}

.header h1 {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(to right, #a78bfa, #f472b6);
  -webkit-background-clip: text;
  color: transparent;
}

.icon-btn {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  border-radius: 50%;
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.content {
  display: flex;
  flex: 1;
  gap: 1rem;
  min-height: 0;
}

.grid-section {
  flex: 3;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.mode-toggle {
  display: flex;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 4px;
}

.toggle-btn {
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

.grid-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 1.5rem;
  row-gap: 15rem;
  overflow-y: auto;
  padding-right: 0.5rem;
  flex: 1;
}

.grid-item {
  aspect-ratio: 180 / 250;
  border-radius: 50% 50% 20% 20% / 36% 36% 16% 16%;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
  background: #000;
  position: relative;
  box-shadow: 0 0 0 2px #8b5cf6;
}

.set-item .set-preview {
  display: flex;
  width: 100%;
  height: 100%;
}
.set-item .set-preview img {
  width: 50%;
  height: 100%;
  object-fit: cover;
}

.grid-item > img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.set-name {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: rgba(0,0,0,0.7);
  color: white;
  text-align: center;
  padding: 0.5rem 0;
  font-size: 0.8rem;
  font-weight: bold;
}

.grid-item:hover {
  box-shadow: 0 0 0 4px #f472b6;
  transform: scale(1.05);
}

.grid-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  color: #e5e7eb;
}

.page-btn {
  background: rgba(139, 92, 246, 0.2);
  color: #a78bfa;
  border: 1px solid rgba(139, 92, 246, 0.4);
  padding: 0.5rem 1rem;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.page-btn:not(:disabled):hover {
  background: rgba(139, 92, 246, 0.4);
  color: white;
}

.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.upload-section {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.qr-container {
  background: white;
  padding: 10px;
  border-radius: 12px;
}

.qr-container img {
  display: block;
  width: 150px;
  height: 150px;
}
</style>
