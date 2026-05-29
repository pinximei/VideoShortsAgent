<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

const route = useRoute();
const pageTitle = computed(() => {
  const m: Record<string, string> = {
    "/": "总览",
    "/jobs": "任务列表",
  };
  if (route.path.startsWith("/jobs/")) return `任务 #${route.params.id}`;
  if (route.path.startsWith("/pending/")) return "待发布";
  return m[route.path] || "Pipeline";
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
      </nav>

      <div class="nav-section">待发布</div>
      <nav class="nav">
        <RouterLink to="/pending/douyin">🎵 抖音</RouterLink>
        <RouterLink to="/pending/xhs">📕 小红书</RouterLink>
        <RouterLink to="/pending/toutiao">📰 今日头条</RouterLink>
        <RouterLink to="/pending/douban">🫘 豆瓣</RouterLink>
      </nav>

      <div class="sidebar-foot">
        Soul 只产内容<br />
        本服务负责去重、Brief、文案包<br />
        VSA 本地出片（可选）
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
