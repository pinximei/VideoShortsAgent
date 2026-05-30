<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { api, type Theme } from "./api";

const route = useRoute();
const themes = ref<Theme[]>([]);

const pageTitle = computed(() => {
  const m: Record<string, string> = {
    "/": "总览",
    "/jobs": "任务列表",
    "/publishing": "发布运营",
    "/settings/channels": "渠道账号",
    "/settings/publisher": "发布批次",
    "/settings/llm": "DeepSeek 编排",
  };
  if (route.path.startsWith("/jobs/")) return `任务 #${route.params.id}`;
  if (route.path.startsWith("/pending/")) return "待发布";
  return m[route.path] || "Pipeline";
});

const channelLabels: Record<string, string> = {
  douyin: "抖音",
  xhs: "小红书",
  toutiao: "今日头条",
  douban: "豆瓣",
};

onMounted(async () => {
  try {
    themes.value = await api.themes();
  } catch {
    themes.value = [];
  }
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">AiSoul Pipeline</div>
      <div class="brand-sub">内容编排中控台</div>

      <div class="nav-section">工作台</div>
      <nav class="nav">
        <RouterLink to="/">📊 总览</RouterLink>
        <RouterLink to="/publishing">📈 发布运营</RouterLink>
        <RouterLink to="/jobs">📋 任务列表</RouterLink>
        <RouterLink to="/settings/channels">⚙️ 渠道账号</RouterLink>
        <RouterLink to="/settings/publisher">🖥️ 发布批次</RouterLink>
        <RouterLink to="/settings/llm">🤖 DeepSeek 编排</RouterLink>
      </nav>

      <template v-for="t in themes" :key="t.id">
        <div class="nav-section">待发布 · {{ t.label }}</div>
        <nav class="nav">
          <RouterLink
            v-for="(label, ch) in channelLabels"
            :key="t.id + ch"
            :to="{ path: `/pending/${ch}`, query: { theme: t.id } }"
          >
            {{ label }}
          </RouterLink>
        </nav>
      </template>

      <div class="sidebar-foot">
        一账号一赛道<br />
        Soul 产内容 → 中间层分赛道打包<br />
        各平台独立账号维护
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <span class="topbar-title">{{ pageTitle }}</span>
        <span class="muted">本地服务 · 127.0.0.1:8780</span>
      </header>
      <div class="content">
        <RouterView />
      </div>
    </div>
  </div>
</template>
