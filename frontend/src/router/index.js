import { createRouter, createWebHistory } from 'vue-router'
import TouchscreenView from '../views/TouchscreenView.vue'
import RemoteUploadView from '../views/RemoteUploadView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'touchscreen',
      component: TouchscreenView
    },
    {
      path: '/upload',
      name: 'remoteUpload',
      component: RemoteUploadView
    },
    {
      path: '/gallery',
      name: 'gallery',
      component: () => import('../views/GalleryView.vue')
    }
  ]
})

export default router
