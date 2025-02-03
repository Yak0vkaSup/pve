<template>
  <header class="header">
    <nav class="navbar">
      <div class="logo">
        <router-link to="/">pve</router-link>
      </div>
      <ul class="nav-links">
        <li>
          <router-link to="/factory">Factory</router-link>
        </li>
        <li>
          <router-link to="/port">Port</router-link>
        </li>
        <li>
          <router-link to="/docs">Docs</router-link>
        </li>
      </ul>
      <div class="auth-section">
        <button v-if="!authStore.isAuthenticated" @click="showLogin = true">Login</button>
        <div v-else class="profile-wrapper">
          <router-link to="/profile">
            <div class="profile-button">
              <img :src="authStore.userInfo?.photo_url || defaultProfileImage" alt="User Profile" />
            </div>
          </router-link>
        </div>
      </div>
    </nav>
    <Login v-if="showLogin" @close="showLogin = false" />
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import Login from './Login.vue';
import defaultProfileImage from '../assets/default.png';
import '../assets/inputs.css'
const authStore = useAuthStore();
const showLogin = ref(false);

// Initialize authentication state
onMounted(() => {
  // authStore.initializeAuth();
  // if (!authStore.isAuthenticated) {
  //   authStore.logout();  // Log the user out if auth initialization fails
  //   showLogin.value = true;  // Optionally, show the login modal again
  // }
});

</script>

<style scoped>
.header {
  color: #fff;
  padding: 1rem;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 3vh;
}

.logo a {
  color: #fff;
  text-decoration: none;
  font-size: 1.5rem;
}

.nav-links {
  list-style: none;
  display: flex;
  gap: 10rem;
}

.nav-links a {
  color: #fff;
  text-decoration: none;
}

.auth-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}
/* Profile Button Styles */
.profile-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.profile-button {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background-color: #f0f0f0;
  border: 2px solid #ccc;
  transition: border-color 0.3s ease;
}

.profile-button:hover {
  border-color: white;
}

.profile-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
