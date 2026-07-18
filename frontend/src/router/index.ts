import { createRouter, createWebHistory } from "vue-router";

import { useAuth } from "../auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "zones",
      component: () => import("../views/ZonesView.vue"),
    },
    {
      path: "/zones/:zoneId",
      name: "zone-detail",
      component: () => import("../views/ZoneDetailView.vue"),
      props: true,
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
      meta: { public: true },
    },
    {
      path: "/callback",
      name: "callback",
      component: () => import("../views/CallbackView.vue"),
      meta: { public: true },
    },
  ],
});

// The whole app sits behind this — anonymous visitors never reach the zone
// list or detail views, only /login and the OIDC /callback redirect target.
router.beforeEach((to) => {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated.value) {
    return to.name === "login" ? { name: "zones" } : true;
  }
  return to.meta.public ? true : { name: "login", query: { redirect: to.fullPath } };
});

export default router;
