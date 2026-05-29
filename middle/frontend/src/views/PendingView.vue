<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { api, type Theme } from "../api";

const props = defineProps<{ channel: string }>();
const route = useRoute();
const themeId = computed(() => String(route.query.theme || ""));

const channelLabels: Record<string, string> = {
  douyin: "抖音",
  xhs: "小红书",
  toutiao: "今日头条",
  douban: "豆瓣",
};

const label = computed(() => channelLabels[props.channel] || props.channel);
const themes = ref<Theme[]>([]);
const themeLabel = computed(
  () => themes.value.find((t) => t.id === themeId.value)?.label || themeId.value || "全部赛道"
);
const accountLabel = computed(() => {
  const t = themes.value.find((x) => x.id === themeId.value);
  if (!t?.accounts) return "";
  return t.accounts[props.channel]?.label || "";
});

const rows = ref<Record<string, unknown>[]>([]);
const err = ref("");

async function load() {
  try {
    rows.value = await api.pending(props.channel, themeId.value || undefined);
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

function titleOf(j: Record<string, unknown>) {
  return (j.soul_snapshot as Record<string, unknown>)?.title || "—";
}

onMounted(async () => {
  try {
    themes.value = await api.themes();
  } catch {
    themes.value = [];
  }
  await load();
});

watch([() => props.channel, themeId], load);
</script>

<template>
  <h1>待发布 · {{ themeLabel }} · {{ label }}</h1>
  <p class="lead">
    <span v-if="accountLabel" class="badge">{{ accountLabel }}</span>
    已打包但未在该账号标记「{{ label }}」已发布的任务。
  </p>

  <div class="row-actions">
    <button class="btn btn-ghost" @click="load">刷新</button>
    <RouterLink to="/jobs" class="btn btn-ghost">全部任务</RouterLink>
  </div>

  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>

  <div v-if="rows.length" class="panel" style="padding: 0; overflow: hidden">
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>标题</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="j in rows" :key="String(j.content_key)">
          <td>{{ j.article_id }}</td>
          <td>{{ titleOf(j) }}</td>
          <td>
            <RouterLink :to="`/jobs/${j.article_id}`" class="btn btn-ghost btn-sm">打开详情</RouterLink>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <div v-else class="panel empty">🎉 当前赛道没有待发布任务</div>
</template>
