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
  margin: 0;
  width: 100vw;
  height: 100vh;
  box-sizing: border-box;

}
</style>
