<template>
  <div class="app-container">
    <Header />
    <router-view />
    <Footer />
  </div>
</template>

<script setup lang="ts">
import Header from './components/Header.vue';
import Footer from './components/Footer.vue';

</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  /* Center the container horizontally */
  margin: 0 auto;
  /* Set a maximum width */
  max-width: 1200px;
  /* Allow the width to adjust based on viewport */
  width: 100%;
  /* Ensure padding doesn't affect total width */
  box-sizing: border-box;
  /* Optional padding */
  padding: 0 20px;
}
</style>
