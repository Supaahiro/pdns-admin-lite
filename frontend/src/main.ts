import { createApp } from "vue";

import App from "./App.vue";
import { initAuth } from "./auth";
import router from "./router";
import "./style.css";

// Awaited before mount so the UI doesn't flash logged-out then logged-in.
initAuth().finally(() => {
  createApp(App).use(router).mount("#app");
});
