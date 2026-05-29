<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { api } from "../api";

const data = ref<Record<string, unknown> | null>(null);
const err = ref("");

async function load() {
  try {
    data.value = await api.publisherOverview();
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

onMounted(load);
</script>

<template>
  <h1>发布批次 · 双浏览器</h1>
  <p class="lead">
    固定 <strong>2 个批次 ID</strong> 绑定 2 个无头浏览器槽位；每账号独立 Profile 目录保留登录态。
    上传发布由 <strong>固定 Playwright 脚本</strong> 执行，不使用大模型点网页。
  </p>

  <div class="row-actions">
    <button class="btn btn-ghost" @click="load">刷新</button>
    <RouterLink to="/settings/channels" class="btn btn-ghost">渠道账号配置</RouterLink>
  </div>

  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>
  <p v-if="data?.note" class="muted">{{ data.note }}</p>

  <div v-if="data?.slots" class="account-grid">
    <div
      v-for="slot in data.slots as Record<string, unknown>[]"
      :key="String(slot.batch_id)"
      class="account-card"
    >
      <div class="account-card__head">
        <span class="account-card__title">
          槽位 {{ slot.slot_id }} · {{ slot.batch_id }}
        </span>
        <span class="badge">{{ slot.label }}</span>
      </div>
      <p v-if="slot.batch" class="muted">
        站点 {{ (slot.batch as Record<string, string>).site_code }}
        · 赛道 {{ (slot.batch as Record<string, string>).theme_id }}
      </p>
      <ul class="file-list">
        <li
          v-for="acc in (slot.accounts as Record<string, unknown>[]) || []"
          :key="String(acc.id)"
        >
          {{ acc.channel_id }} — {{ acc.label || acc.handle }}
          <span class="muted">
            · 登录 {{ (acc.session as Record<string, string>)?.status || "unknown" }}
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>
