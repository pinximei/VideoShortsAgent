<script setup lang="ts">
defineProps<{
  value: number;
  label?: string;
}>();
</script>

<template>
  <div class="progress-wrap">
    <div v-if="label" class="progress-label">
      <span>{{ label }}</span>
      <span>{{ Math.round(value) }}%</span>
    </div>
    <div class="progress-track" role="progressbar" :aria-valuenow="value" aria-valuemin="0" aria-valuemax="100">
      <div class="progress-fill" :style="{ width: `${Math.min(100, Math.max(0, value))}%` }" />
    </div>
  </div>
</template>

<style scoped>
.progress-wrap {
  margin-bottom: 16px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--vsa-text-muted);
  margin-bottom: 8px;
}

.progress-track {
  height: 6px;
  border-radius: 999px;
  background: var(--vsa-surface-2);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--vsa-primary), #a78bfa);
  transition: width 0.25s ease;
}
</style>
