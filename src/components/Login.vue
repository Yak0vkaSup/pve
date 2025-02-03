<!-- src/components/Login.vue -->
<template>
  <div class="modal-overlay" @click.self="close">
    <div class="modal">
      <div class="telegram-container">
        <div id="telegram-login" v-if="!authStore.isAuthenticated"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';

// Props
const emit = defineEmits(['close']);

// Store
const authStore = useAuthStore();

// Declare global interface augmentation
declare global {
  interface Window {
    onTelegramAuth: (user: any) => void;
  }
}

// Function to close the modal
function close() {
  emit('close');
}

// Function to handle Telegram authentication
window.onTelegramAuth = function (user: any) {
  // Store user info locally
  localStorage.setItem('telegramUser', JSON.stringify(user));
  authStore.login(
    {
      id: user.id,
      first_name: user.first_name,
      last_name: user.last_name || '',
      username: user.username || '',
      photo_url: user.photo_url || ''
    },
    '' // Token will be set after backend response
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
  fetch('https://pve.finance/api/telegram-auth', {
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
      }
    })
    .catch((error) => {
      console.error('Error sending data to server:', error);
    });

};

// Dynamically load the Telegram login widget script
onMounted(() => {
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
  background-color: transparent; /* Make modal background transparent to see Telegram widget */
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
