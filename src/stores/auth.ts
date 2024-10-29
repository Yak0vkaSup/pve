// src/stores/auth.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

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
  }

  function logout() {
    userInfo.value = null;
    token.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem('userToken');
    localStorage.removeItem('telegramUser');
  }

  function initializeAuth() {
    const storedToken = localStorage.getItem('userToken');
    const storedUser = localStorage.getItem('telegramUser');

    if (storedToken && storedUser) {
      userInfo.value = JSON.parse(storedUser);
      token.value = storedToken;
      isAuthenticated.value = true;
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
