/// <reference types="vite/client" />

// Baked in at container build time (see ../Dockerfile); undefined outside a
// release build (e.g. `npm run dev`) — App.vue falls back to "0.0.0-dev.0" then.
interface ImportMetaEnv {
  readonly VITE_APP_VERSION: string;
  readonly VITE_APP_SHA: string;
  readonly VITE_APP_BUILD_DATE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Populated at container *start* time by docker-entrypoint.d/ (envsubst over
// public/env.template.js), not at build time — see ../Dockerfile. Absent in
// `npm run dev` and in any build where env.js failed to load.
interface Window {
  __ENV__?: {
    ENVIRONMENT?: string;
  };
}
