<template>
  <div class="telegram-container">
    <!-- Telegram login button -->
    <div id="telegram-login" v-if="!userLoggedIn"></div>

    <!-- Profile button that appears after login -->
    <div v-if="userLoggedIn" class="profile-button" @click="toggleUserInfo">
      <img :src="userInfo.photo_url || defaultProfileImage" alt="User Profile" />
    </div>

    <!-- Modal to display and edit user info -->
    <div v-if="showUserInfo" class="user-info-modal">
      <h2>User Information</h2>

      <p><strong>ID:</strong> {{ userInfo.id }}</p>

      <div>
        <label for="firstName">First Name:</label>
        <input v-model="editableUser.first_name" id="firstName" type="text" />
      </div>

      <div>
        <label for="lastName">Last Name:</label>
        <input v-model="editableUser.last_name" id="lastName" type="text" />
      </div>

      <div>
        <label for="username">Username:</label>
        <input v-model="editableUser.username" id="username" type="text" disabled />
      </div>

      <div>
        <label for="key">Key:</label>
        <input v-model="editableUser.key" id="key" type="text" placeholder="Enter your key" />
      </div>

      <div>
        <label for="keySecret">Key Secret:</label>
        <input
          v-model="editableUser.key_secret"
          id="keySecret"
          type="password"
          placeholder="Enter your key secret"
        />
      </div>

      <div class="buttons-container">
        <button @click="saveUserData">Save</button>
        <button @click="toggleUserInfo">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

// States to track user session and modal visibility
const userLoggedIn = ref(false)
const showUserInfo = ref(false)
const userInfo = ref(null)
const editableUser = reactive({
  first_name: '',
  last_name: '',
  username: '',
  key: '',
  key_secret: ''
})
const defaultProfileImage = './assets/default.png' // Make sure to set this to an actual image path

// Function to toggle the user info modal
function toggleUserInfo() {
  showUserInfo.value = !showUserInfo.value
}

// Function to handle the user login via Telegram
window.onTelegramAuth = function (user) {
  // Store user info locally
  localStorage.setItem('telegramUser', JSON.stringify(user))
  userInfo.value = user
  userLoggedIn.value = true

  // Create the data object to send to the backend
  const userData = {
    id: user.id,
    first_name: user.first_name,
    last_name: user.last_name || '',
    username: user.username || '',
    photo_url: user.photo_url || '',
    auth_date: user.auth_date,
    hash: user.hash
  }
  console.log(userData)
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
      console.log('Response from server:', data)
      if (data.status === 'success') {
        // Save the token to localStorage
        localStorage.setItem('userToken', data.token)
        console.log('Token saved to localStorage:', data.token)
      }
    })
    .catch((error) => {
      console.error('Error sending data to server:', error)
    })

  // Optionally hide or disable the login button
  const loginContainer = document.getElementById('telegram-login')
  if (loginContainer) {
    loginContainer.style.display = 'none' // Hide login button after login
  }
}

// Function to fetch user data from the backend
function fetchUserData(userId) {
  fetch('https://pve.finance/api/user-data', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ user: { id: userId } })
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === 'success' && data.user_info) {
        const userData = data.user_info
        // Populate editableUser with fetched data
        editableUser.first_name = userData.first_name
        editableUser.last_name = userData.last_name
        editableUser.username = userData.username
        editableUser.key = userData.key || ''
        editableUser.key_secret = userData.key_secret || ''
        // Set userInfo for general display
        userInfo.value = userData
      } else {
        console.error('User data not found or error occurred')
      }
    })
    .catch((error) => {
      console.error('Error fetching user data:', error)
    })
}

// Function to send updated user data to the backend
function saveUserData() {
  const updatedUser = {
    id: userInfo.value.id,
    first_name: editableUser.first_name,
    last_name: editableUser.last_name,
    username: editableUser.username,
    key: editableUser.key,
    key_secret: editableUser.key_secret
  }

  // Send the updated data to the backend
  fetch('https://pve.finance/api/update-user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(updatedUser)
  })
    .then((response) => response.json())
    .then((data) => {
      console.log('Response from server:', data)
      toggleUserInfo() // Close the modal
    })
    .catch((error) => {
      console.error('Error updating user data:', error)
    })
}

// Handle profile image error
function handleImageError(event) {
  event.target.src = defaultProfileImage // Fallback to default image
}

// Dynamically load the Telegram login widget script
onMounted(() => {
  const user = JSON.parse(localStorage.getItem('telegramUser'))
  if (user) {
    // If user info is already in local storage, set user state
    userInfo.value = user
    userLoggedIn.value = true
    fetchUserData(user.id) // Fetch user data from backend
  } else {
    // Otherwise, load the Telegram login widget
    const script = document.createElement('script')
    script.async = true
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.setAttribute('data-telegram-login', 'pvetrader_bot')
    script.setAttribute('data-size', 'large')
    script.setAttribute('data-request-access', 'write')
    script.setAttribute('data-onauth', 'onTelegramAuth(user)')
    document.getElementById('telegram-login').appendChild(script)
  }
})
</script>

<style scoped>
.telegram-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  width: 100%;
}

.profile-button {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background-color: #f0f0f0;
  border: 2px solid #ccc;
}

.profile-button img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-info-modal {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: #181818; /* Make the modal grey */
  padding: 2rem;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  border-radius: 10px; /* Makes the modal rounded */
  color: white; /* Make text inside the modal white */
}

button {
  padding: 10px 20px;
  margin: 10px 10px; /* Adjust margin to align buttons properly */
  border: none;
  background-color: #4caf50;
  color: white;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: #45a049;
}

.buttons-container {
  display: flex;
  justify-content: center; /* Align buttons horizontally */
}

input {
  width: 100%;
  padding: 8px;
  margin: 5px 0;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #181818; /* Grey background for input */
  color: white; /* White text inside input */
}

input::placeholder {
  color: #ccc; /* Light grey color for placeholder text */
}

input[type='password'] {
  font-family: sans-serif;
}

input:focus {
  border-color: #4caf50; /* Green border on focus */
  outline: none;
}
</style>
