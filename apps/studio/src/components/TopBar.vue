<script setup lang="ts">
import { onMounted, ref } from "vue";
import { isTauri, tauriInvoke } from "@/composables/useTauri";

defineProps<{ title: string }>();

const edition = ref("免费版");

onMounted(async () => {
  if (!isTauri()) return;
  try {
    const s = await tauriInvoke<{ edition: string }>("license_status");
    edition.value = s.edition === "pro" ? "专业版" : "免费版";
  } catch {
    /* default */
  }
});
</script>

<template>
  <header class="topbar card-glass">
    <h1 class="title page-title">{{ title }}</h1>
    <div class="actions">
      <span :class="edition === '专业版' ? 'badge-pro' : 'badge-free'">{{ edition }}</span>
      <button type="button" class="btn btn-secondary btn-sm">使用说明</button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  border-bottom: 1px solid var(--vsa-border-subtle);
  box-shadow: var(--vsa-shadow-sm);
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 650;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-sm {
  height: 36px;
  padding: 0 16px;
  font-size: 13px;
}
</style>
