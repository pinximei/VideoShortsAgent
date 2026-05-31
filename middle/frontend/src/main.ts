import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import App from "./App.vue";
import "./style.css";
import DashboardView from "./views/DashboardView.vue";
import JobsView from "./views/JobsView.vue";
import JobDetailView from "./views/JobDetailView.vue";
import PendingView from "./views/PendingView.vue";
import PublishingView from "./views/PublishingView.vue";
import ChannelConfigView from "./views/ChannelConfigView.vue";
import PublisherBatchesView from "./views/PublisherBatchesView.vue";
import LlmSettingsView from "./views/LlmSettingsView.vue";
import TtsSettingsView from "./views/TtsSettingsView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: DashboardView },
    { path: "/jobs", component: JobsView },
    { path: "/jobs/:id", component: JobDetailView, props: true },
    { path: "/pending/:channel", component: PendingView, props: true },
    { path: "/publishing", component: PublishingView },
    { path: "/settings/channels", component: ChannelConfigView },
    { path: "/settings/publisher", component: PublisherBatchesView },
    { path: "/settings/llm", component: LlmSettingsView },
    { path: "/settings/tts", component: TtsSettingsView },
  ],
});

createApp(App).use(router).mount("#app");
