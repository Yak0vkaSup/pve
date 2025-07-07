<!-- src/views/UserProfile.vue -->
<template>
  <div class="profile-container">
    <div class="profile-content">
      <form @submit.prevent="saveUserData" class="profile-form">
        <div class="profile-picture">
          <img :src="authStore.userInfo?.photo_url || defaultProfileImage" alt="User Profile" />
        </div>
        <div class="form-group">
          <label for="firstName">First Name:</label>
          <input
            v-model="form.first_name"
            id="firstName"
            type="text"
            class="input"
            :class="{ 'input-error': errors.first_name }"
            required
            aria-required="true"
          />
          <span v-if="errors.first_name" class="error-text">{{ errors.first_name }}</span>
        </div>

        <div class="form-group">
          <label for="lastName">Last Name:</label>
          <input
            v-model="form.last_name"
            id="lastName"
            type="text"
            class="input"
            :class="{ 'input-error': errors.last_name }"
            required
            aria-required="true"
          />
          <span v-if="errors.last_name" class="error-text">{{ errors.last_name }}</span>
        </div>

        <div class="form-group">
          <label for="username">Username:</label>
          <input
            v-model="form.username"
            id="username"
            type="text"
            class="input"
            disabled
            aria-disabled="true"
          />
        </div>

        <div class="buttons-container">
          <button type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? 'Saving...' : 'Save' }}
          </button>
          <button type="button" class="secondary" @click="handleLogout">
            Logout
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import defaultProfileImage from '../assets/default.png';
import { useRouter } from 'vue-router';
import { toast, type ToastOptions } from 'vue3-toastify';
import '../assets/inputs.css';

// Initialize stores and utilities
const authStore = useAuthStore();
const router = useRouter();

// Define reactive form data
const form = reactive({
  first_name: '',
  last_name: '',
  username: '',
});

// Define reactive errors object
const errors = reactive({
  first_name: '',
  last_name: '',
});

// Reactive states for loading
const isSubmitting = ref(false);

// Define common ToastOptions
const toastOptions: ToastOptions = {
  autoClose: 1000,
  position: toast.POSITION.BOTTOM_RIGHT,
};

// Initialize form with user data
onMounted(() => {
  if (authStore.userInfo) {
    form.first_name = authStore.userInfo.first_name;
    form.last_name = authStore.userInfo.last_name;
    form.username = authStore.userInfo.username;
  }
});

// Function to handle logout
const handleLogout = () => {
  authStore.logout();
  router.push({ name: 'Home' });
};

// Function to validate form inputs
function validateForm(): boolean {
  let isValid = true;
  errors.first_name = '';
  errors.last_name = '';

  if (!form.first_name.trim()) {
    errors.first_name = 'First name is required.';
    isValid = false;
  }

  if (!form.last_name.trim()) {
    errors.last_name = 'Last name is required.';
    isValid = false;
  }

  return isValid;
}

// Function to save user data
async function saveUserData() {
  if (!validateForm()) {
    toast.error('Please fix the errors in the form.', toastOptions);
    return;
  }

  isSubmitting.value = true;

  const userToken = localStorage.getItem('userToken');

  if (!userToken) {
    toast.error('User token not found. Please log in again.', toastOptions);
    isSubmitting.value = false;
    authStore.logout();
    router.push({ name: 'Home' });
    return;
  }

  const updatedUser = {
    id: authStore.userInfo?.id,
    first_name: form.first_name,
    last_name: form.last_name,
    username: authStore.userInfo?.username, // Username remains unchanged
    token: userToken, // Include the token in the request body
  };

  try {
    const response = await fetch('https://pve.finance/api/update-user', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updatedUser),
    });

    const data = await response.json();

    if (data.status === 'success') {
      // Update the store with new user info
      if (authStore.userInfo) {
        authStore.userInfo.first_name = form.first_name;
        authStore.userInfo.last_name = form.last_name;
      }
      toast.success('Profile updated successfully!', toastOptions);

      setTimeout(() => {
        router.push({ name: 'Home' });
      }, 2000);
    } else {
      toast.error(data.message || 'Failed to update profile.', toastOptions);
    }
  } catch (error) {
    console.error('Error updating user data:', error);
    toast.error('An unexpected error occurred. Please try again later.', toastOptions);
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1rem;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.profile-picture {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  margin-bottom: 10px;
}

.profile-picture img {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
  border: 4px solid white;
}

.profile-form {
  width: 100%;
  max-width: 500px;
  margin-top: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: white;
}

.input:focus {
  outline: none;
}

.input-error {
  border-color: #f44336;
}

.error-text {
  color: #f44336;
  font-size: 0.875rem;
}

@media (min-width: 768px) {
  .profile-content {
    flex-direction: row;
    align-items: flex-start;
  }

  .profile-picture {
    margin-right: 2rem;
  }

  .profile-form {
    margin-top: 0;
  }
}
</style>
