<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal">
      <div class="telegram-container">
        <!-- Only show the Telegram widget if NOT dev mode -->
        <div id="telegram-login" v-if="!isDevMode && !authStore.isAuthenticated"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

// Props
const emit = defineEmits(['close']);

// Store and Router
const authStore = useAuthStore();
const router = useRouter();

// 1) Detect dev mode (assuming VITE_APP_ENV=dev in .env)
const isDevMode = import.meta.env.VITE_APP_ENV === 'dev';
const baseURL = isDevMode ? 'http://localhost:5001' : 'https://pve.finance';

// Function to close the modal
function close() {
  emit('close');
}

// In dev mode, we'll send a fake user to the backend:
function devModeLogin() {
  const fakeUser = {
    id: "123456789",
    first_name: "Dev",
    last_name: "User",
    username: "DevUser",
    photo_url: "",
    auth_date: Date.now(),   // The route uses this if is_dev_mode() is false
    hash: "fakehash"         // The route will skip the real hash check if dev mode is True
  };

  // This hits /api/telegram-auth, which in dev mode bypasses the real checks
  fetch(`${baseURL}/api/telegram-auth`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(fakeUser)
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.status === 'success') {
        localStorage.setItem('userToken', data.token);
        localStorage.setItem('userId', fakeUser.id);

        // Log in silently on the frontend store
        authStore.login(
          {
            id: fakeUser.id,
            first_name: fakeUser.first_name,
            last_name: fakeUser.last_name,
            username: fakeUser.username,
            photo_url: fakeUser.photo_url
          },
          data.token
        );
        emit('close');
        // Redirect to Factory page after successful login
        router.push({ name: 'Factory' });
      } else {
        console.error('Dev mode login error:', data.message);
      }
    })
    .catch((error) => {
      console.error('Error sending dev user data to server:', error);
    });
}

// 2) Real Telegram Auth callback (only used if not dev mode)
declare global {
  interface Window {
    onTelegramAuth: (user: any) => void;
  }
}

window.onTelegramAuth = function (user: any) {
  // Store user info locally
  localStorage.setItem('telegramUser', JSON.stringify(user));
  authStore.silent_login(
    {
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name || '',
      username: user.username || '',
      photo_url: user.photo_url || ''
    },
    '' // Token is set after backend response
  );

  // Create the data object to send to the backend
  const userData = {
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name || '',
    username: user.username || '',
    photo_url: user.photo_url || '',
    auth_date: user.auth_date,
    hash: user.hash
  };
  // Send the data to the backend
  fetch(`${baseURL}/api/telegram-auth`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(userData)
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success') {
        localStorage.setItem('userToken', data.token);
        localStorage.setItem('userId', user.id);
        authStore.login(authStore.userInfo!, data.token);
        emit('close');
        // Redirect to Factory page after successful login
        router.push({ name: 'Factory' });
      }
    })
    .catch((error) => {
      console.error('Error sending data to server:', error);
    });
};

// Dynamically load the Telegram login widget script
onMounted(() => {
  if (isDevMode) {
    devModeLogin();
    return;
  }

  // Production: actually load the Telegram widget
  if (!authStore.isAuthenticated) {
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', 'pvetrader_bot');
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-userpic', 'false');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-onauth', 'onTelegramAuth(user)');
    document.getElementById('telegram-login')?.appendChild(script);
  }
});
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal {
  background-color: transparent;
  padding: 0;
}
.telegram-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}
</style>
