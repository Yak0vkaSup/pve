import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import Toast from 'vue-toastification';
import { createPinia } from 'pinia';
import './assets/main.css';

const app = createApp(App);

const pinia = createPinia();
app.use(pinia);

app.use(router);
app.use(Toast, {
  timeout: 5000,
  position: 'bottom-right',
});

app.mount('#app');