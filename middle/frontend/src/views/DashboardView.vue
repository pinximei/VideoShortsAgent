<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { api } from "../api";

const dash = ref<Record<string, unknown> | null>(null);
const running = ref(false);
const err = ref("");
const ok = ref("");
let timer: number | undefined;

async function load() {
  try {
    dash.value = await api.dashboard();
    const run = (dash.value?.run as Record<string, unknown>) || {};
    running.value = Boolean(run.running);
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

async function startRun() {
  ok.value = "";
  try {
    await api.run();
    running.value = true;
    ok.value = "已启动一轮同步，请稍候刷新…";
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

onMounted(() => {
  load();
  timer = window.setInterval(load, 4000);
});
onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>

<template>
  <h1>总览</h1>
  <p class="lead">从 Soul 拉取高价值内容 → 生成短视频 Brief 与多平台文案 → 记录发布状态。</p>

  <div class="row-actions">
    <button class="btn btn-primary" :disabled="running" @click="startRun">
      {{ running ? "同步运行中…" : "▶ 立即同步一轮" }}
    </button>
    <button class="btn btn-ghost" @click="load">刷新</button>
    <span v-if="running" class="muted"><span class="dot dot-run" /> 运行中</span>
    <span v-else class="muted"><span class="dot dot-idle" /> 空闲</span>
  </div>

  <p v-if="ok" class="muted" style="color: #86efac">{{ ok }}</p>
  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>

  <div v-if="dash" class="cards">
    <div class="card highlight">
      <div class="label">任务总数</div>
      <div class="value">{{ dash.total_jobs }}</div>
    </div>
    <div v-for="(n, st) in (dash.job_counts as Record<string, number>)" :key="st" class="card">
      <div class="label">{{ st }}</div>
      <div class="value">{{ n }}</div>
    </div>
  </div>

  <div v-if="dash?.pending_by_theme_channel" class="panel">
    <div class="panel-title">各赛道 · 渠道待发布</div>
    <table>
      <thead>
        <tr>
          <th>赛道</th>
          <th>抖音</th>
          <th>小红书</th>
          <th>头条</th>
          <th>豆瓣</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(cols, tid) in (dash.pending_by_theme_channel as Record<string, Record<string, number>>)"
          :key="tid"
        >
          <td>{{ (dash.themes as { id: string; label: string }[])?.find((t) => t.id === tid)?.label || tid }}</td>
          <td v-for="ch in ['douyin', 'xhs', 'toutiao', 'douban']" :key="ch">
            <RouterLink
              v-if="cols[ch]"
              :to="{ path: `/pending/${ch}`, query: { theme: tid } }"
              class="btn btn-ghost btn-sm"
            >
              {{ cols[ch] }}
            </RouterLink>
            <span v-else class="muted">0</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="dash?.pending_publish" class="panel">
    <div class="panel-title">全渠道待发布合计</div>
    <div class="cards" style="margin-bottom: 0">
      <RouterLink
        v-for="(n, ch) in (dash.pending_publish as Record<string, number>)"
        :key="ch"
        :to="`/pending/${ch}`"
        class="card"
        style="text-decoration: none; color: inherit"
      >
        <div class="label">{{ ch }}</div>
        <div class="value">{{ n }}</div>
      </RouterLink>
    </div>
  </div>

  <div v-if="dash?.run" class="panel">
    <div class="panel-title">最近一次运行</div>
    <pre v-if="(dash.run as Record<string, unknown>).last_run" class="pre">{{
      JSON.stringify((dash.run as Record<string, unknown>).last_run, null, 2)
    }}</pre>
    <p v-else class="muted">尚未运行，点击上方按钮开始。</p>
    <p v-if="(dash.run as Record<string, unknown>).last_error" class="muted" style="color: #fca5a5">
      {{ (dash.run as Record<string, unknown>).last_error }}
    </p>
  </div>
</template>
