<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<template>
  <header class="page-header">
    <div>
      <h2 class="h2 page-title">{{ title }}</h2>
      <p v-if="description" class="desc">{{ description }}</p>
    </div>
    <slot name="actions" />
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.h2 {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.desc {
  margin: 0;
  color: var(--vsa-text-muted);
  max-width: 56ch;
  font-size: 14px;
}
</style>
