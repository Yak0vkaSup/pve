// src/router/index.ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '../stores/auth';

import Home from '../views/Home.vue';
import UserProfile from '../views/UserProfile.vue';
import Factory from '../views/Factory.vue';
import Port from '../views/Port.vue';

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
    meta: { requiresAuth: false },
  },
  {
    path: '/factory',
    name: 'Factory',
    component: Factory,
    meta: { requiresAuth: false },
  },
  {
    path: '/port',
    name: 'Port',
    component: Port,
    meta: { requiresAuth: false },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// Navigation Guard to Protect Routes
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Redirect unauthenticated users to the Home page
    next({ name: 'Home' });
  } else {
    next();
  }
});

export default router;
