/*
 * Application bootstrap: Pinia, router, PrimeVue (TravelPreset + services),
 * then restore the persisted theme/accent before mounting.
 */
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import 'primeicons/primeicons.css';
import './assets/main.css';

import { createPinia } from 'pinia';
import PrimeVue from 'primevue/config';
import ConfirmationService from 'primevue/confirmationservice';
import ToastService from 'primevue/toastservice';
import Tooltip from 'primevue/tooltip';
import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import { TravelPreset } from './theme/preset';
import { useUiStore } from './stores/ui';

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(PrimeVue, {
  theme: {
    preset: TravelPreset,
    options: { darkModeSelector: '.dark', cssLayer: false }
  }
});
app.use(ToastService);
app.use(ConfirmationService);
app.directive('tooltip', Tooltip);

// Restore persisted theme before mount.
const ui = useUiStore();
ui.initTheme();

app.mount('#app');
