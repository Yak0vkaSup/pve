import { defineStore } from 'pinia';
import { ref } from 'vue';
import { toast } from 'vue3-toastify';
import axios from 'axios';

const pve = { position: toast.POSITION.BOTTOM_RIGHT };

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

  // Check if the app is running in development mode
  const isDevMode = import.meta.env.VITE_APP_ENV === 'development';

  function login(user: UserInfo, userToken: string) {
    userInfo.value = user;
    token.value = userToken;
    isAuthenticated.value = true;
    localStorage.setItem('userToken', userToken);
    localStorage.setItem('telegramUser', JSON.stringify(user));
    toast.success('User logged in successfully', pve);
  }

  function silent_login(user: UserInfo, userToken: string) {
    userInfo.value = user;
    token.value = userToken;
    isAuthenticated.value = true;
    localStorage.setItem('userToken', userToken);
    localStorage.setItem('telegramUser', JSON.stringify(user));
  }

  function silent_logout() {
    userInfo.value = null;
    token.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem('userToken');
    localStorage.removeItem('telegramUser');
  }

  function logout() {
    userInfo.value = null;
    token.value = null;
    isAuthenticated.value = false;
    localStorage.removeItem('userToken');
    localStorage.removeItem('telegramUser');
    toast.success('User logged out successfully', pve);
  }

  async function initializeAuth() {
    if (isDevMode) {
      console.log("Development mode detected: Auto-login enabled");

      const fakeUser: UserInfo = {
        id: "6059244396",
        first_name: "Andrew",
        last_name: "",
        username: "",
        photo_url: "",
      };

      const fakeToken = "f2c606c9-0f5f-424e-8839-f4d74e50c571";
      login(fakeUser, fakeToken);
      return;
    }

    const storedToken = localStorage.getItem('userToken');
    const storedUser = localStorage.getItem('telegramUser');

    if (storedToken && storedUser) {
      userInfo.value = JSON.parse(storedUser);
      token.value = storedToken;

      try {
        const response = await axios.post('/api/verify-token', {
          id: userInfo.value?.id ?? '',
          token: storedToken,
        });

        if (response.data.status === 'success') {
          isAuthenticated.value = true;
          toast.success('User authorised successfully', pve);
        } else {
          isAuthenticated.value = false;
          logout();
        }
      } catch (error) {
        isAuthenticated.value = false;
        toast.error('User is not authorised', pve);
        logout();
      }
    } else {
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
    silent_login,
    silent_logout,
  };
});
