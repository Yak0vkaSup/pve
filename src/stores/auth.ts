// src/stores/auth.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import { toast } from 'vue3-toastify'
const pve = {position: toast.POSITION.BOTTOM_RIGHT}

interface UserInfo {
  id: string;
  first_name: string;
  last_name: string;
  username: string;
  photo_url?: string;
}

export const useAuthStore = defineStore('auth', () => {
  const isAuthenticated = ref(false);
  const userInfo = ref<UserInfo | null>(null);
  const token = ref<string | null>(null);

  function login(user: UserInfo, userToken: string) {
    userInfo.value = user;
    token.value = userToken;
    isAuthenticated.value = true;
    localStorage.setItem('userToken', userToken);
    localStorage.setItem('telegramUser', JSON.stringify(user));
    toast.success('User logged in successfully', pve);
  }

  function logout() {
    userInfo.value = null;
    token.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem('userToken');
    localStorage.removeItem('telegramUser');
    toast.success('User logged out successfully', pve);
  }

  function initializeAuth() {
    const storedToken = localStorage.getItem('userToken');
    const storedUser = localStorage.getItem('telegramUser');

    if (storedToken && storedUser) {
      userInfo.value = JSON.parse(storedUser);
      token.value = storedToken;
      isAuthenticated.value = true;
      toast.success('User authorised successfully', pve);
    }
    if (!storedUser || !storedUser) {
      isAuthenticated.value = false;
      toast.error('User is not authorised', pve);
    }
  }

  return {
    isAuthenticated,
    userInfo,
    token,
    login,
    logout,
    initializeAuth,
  };
});
