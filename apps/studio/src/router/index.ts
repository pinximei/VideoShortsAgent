import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: () => import("@/views/HomeView.vue") },
    { path: "/clip", name: "clip", component: () => import("@/views/ClipView.vue") },
    { path: "/douyin", name: "douyin", component: () => import("@/views/DouyinView.vue") },
    { path: "/ecommerce", name: "ecommerce", component: () => import("@/views/EcommerceView.vue") },
    { path: "/ai", name: "ai", component: () => import("@/views/AiView.vue") },
    { path: "/subtitle", name: "subtitle", component: () => import("@/views/SubtitleView.vue") },
    { path: "/license", name: "license", component: () => import("@/views/LicenseView.vue") },
    { path: "/settings", name: "settings", component: () => import("@/views/SettingsView.vue") },
  ],
});

export default router;
