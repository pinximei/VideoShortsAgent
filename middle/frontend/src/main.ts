import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";
import DashboardView from "./views/DashboardView.vue";
import JobsView from "./views/JobsView.vue";
import JobDetailView from "./views/JobDetailView.vue";
import PendingView from "./views/PendingView.vue";
import PublishingView from "./views/PublishingView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardView },
    { path: "/jobs", component: JobsView },
    { path: "/jobs/:id", component: JobDetailView, props: true },
    { path: "/pending/:channel", component: PendingView, props: true },
    { path: "/publishing", component: PublishingView },
  ],
});

createApp(App).use(router).mount("#app");
