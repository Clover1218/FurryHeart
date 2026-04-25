import { createRouter, createWebHistory } from 'vue-router'
import Index from '@/pages/index.vue'
import Test from '@/pages/test.vue'
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'index',
      component: Index
    },
    {
      path: '/test',
      name: 'test',
      component: Test
    }
  ]
})

export default router
