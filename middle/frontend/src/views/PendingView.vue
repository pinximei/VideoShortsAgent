<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { api } from "../api";

const props = defineProps<{ channel: string }>();
const label = computed(
  () =>
    (
      {
        douyin: "抖音",
        xhs: "小红书",
        toutiao: "今日头条",
        douban: "豆瓣",
      } as Record<string, string>
    )[props.channel] || props.channel
);
const rows = ref<Record<string, unknown>[]>([]);
const err = ref("");

async function load() {
  try {
    rows.value = await api.pending(props.channel);
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

function titleOf(j: Record<string, unknown>) {
  return (j.soul_snapshot as Record<string, unknown>)?.title || "—";
}

onMounted(load);
</script>

<template>
  <h1>待发布 · {{ label }}</h1>
  <p class="lead">已打包但未标记「{{ label }}」已发布的任务。上传后请在详情页点击标记。</p>

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
  <div v-else class="panel empty">🎉 当前没有待发布任务</div>
</template>
