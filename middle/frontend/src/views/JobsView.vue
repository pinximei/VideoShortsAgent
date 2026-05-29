<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { api, type Theme } from "../api";

const jobs = ref<Record<string, unknown>[]>([]);
const themes = ref<Theme[]>([]);
const filter = ref("");
const themeFilter = ref("");
const err = ref("");

const themeMap = () => Object.fromEntries(themes.value.map((t) => [t.id, t.label]));

async function load() {
  try {
    jobs.value = await api.jobs(filter.value || undefined, themeFilter.value || undefined);
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

function titleOf(j: Record<string, unknown>) {
  const snap = j.soul_snapshot as Record<string, unknown> | undefined;
  const brief = j.brief_json as Record<string, unknown> | undefined;
  return snap?.title || brief?.title || "—";
}

function themeLabel(j: Record<string, unknown>) {
  const id = String(j.theme_id || "");
  return themeMap()[id] || id || "—";
}

onMounted(async () => {
  try {
    themes.value = await api.themes();
  } catch {
    themes.value = [];
  }
  await load();
});
</script>

<template>
  <h1>任务列表</h1>
  <p class="lead">每条 Soul 文章对应一个任务，按内容赛道归属不同平台账号。</p>

  <div class="row-actions">
    <select v-model="themeFilter" class="btn btn-ghost" @change="load">
      <option value="">全部赛道</option>
      <option v-for="t in themes" :key="t.id" :value="t.id">{{ t.label }}</option>
    </select>
    <select v-model="filter" class="btn btn-ghost" @change="load">
      <option value="">全部状态</option>
      <option value="ready_to_publish">待发布</option>
      <option value="skipped">已跳过</option>
      <option value="failed">失败</option>
      <option value="discovered,processing">进行中</option>
    </select>
    <button class="btn btn-ghost" @click="load">刷新</button>
  </div>

  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>

  <div v-if="jobs.length" class="panel" style="padding: 0; overflow: hidden">
    <table>
      <thead>
        <tr>
          <th>文章 ID</th>
          <th>赛道</th>
          <th>状态</th>
          <th>标题</th>
          <th>更新时间</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="j in jobs" :key="String(j.content_key)">
          <td>{{ j.article_id }}</td>
          <td><span class="badge">{{ themeLabel(j) }}</span></td>
          <td>
            <span class="badge" :class="'badge-' + j.status">{{ j.status }}</span>
          </td>
          <td>{{ titleOf(j) }}</td>
          <td class="muted">{{ j.updated_at }}</td>
          <td>
            <RouterLink :to="`/jobs/${j.article_id}`" class="btn btn-ghost btn-sm">打开</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="panel empty">暂无任务，请先在总览页点击「立即同步一轮」。</div>
</template>
