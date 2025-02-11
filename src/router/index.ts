// src/router/index.ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '../stores/auth';

import Home from '../views/Home.vue';
import UserProfile from '../views/UserProfile.vue';
import Factory from '../views/Factory.vue';
import Port from '../views/Port.vue';
import Docs from '../views/Docs.vue';
import { toast } from 'vue3-toastify'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: UserProfile,
    meta: { requiresAuth: true },
  },
  {
    path: '/factory',
    name: 'Factory',
    component: Factory,
    meta: { requiresAuth: true },
  },
  {
    path: '/port',
    name: 'Port',
    component: Port,
    meta: { requiresAuth: true },
  },
  {
    path: '/docs',
    name: 'Docs',
    component: Docs,
    meta: { requiresAuth: false },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// Navigation Guard to Protect Routes
router.beforeEach(async (to, from, next) => {
  if (to.meta.requiresAuth) {
    const authStore = useAuthStore();
    await authStore.initializeAuth();
    if (!authStore.isAuthenticated) {
      setTimeout(() => {
        next({ name: 'Home' });
      }, 2000);
      authStore.silent_logout()
      return;
    }
  }
  next();
});

export default router;
