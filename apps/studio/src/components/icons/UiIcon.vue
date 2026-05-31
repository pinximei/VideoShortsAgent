<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  name:
    | "home"
    | "clip"
    | "douyin"
    | "shop"
    | "ai"
    | "subtitle"
    | "key"
    | "settings"
    | "play"
    | "folder"
    | "spark";
  size?: number;
}>();

const size = computed(() => props.size ?? 20);

const paths: Record<string, string> = {
  home: "M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z",
  clip: "M14 4 8 20M10 4 4 20M18 8h4M18 16h4",
  douyin: "M9 6v12l6-4-6-4Zm8 2v8M5 5h2v14H5",
  shop: "M6 6h12l-1.2 12H7.2L6 6Zm3 16a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Zm6 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z",
  ai: "M12 3 9.5 9.5 3 12l6.5 2.5L12 21l2.5-6.5L21 12l-6.5-2.5L12 3Z",
  subtitle: "M4 6h16M4 10h10M4 14h14M4 18h8",
  key: "M14 10a4 4 0 1 0-5.5 5.5L4 20v4h4l4.5-4.5",
  settings:
    "M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm8.5 4a7.2 7.2 0 0 0-.2-1.5l2-1.5-2-3.5-2.3 1a7 7 0 0 0-2.6-1.5L15 2h-4l-.4 3.5a7 7 0 0 0-2.6 1.5l-2.3-1-2 3.5 2 1.5a7.2 7.2 0 0 0 0 3l-2 1.5 2 3.5 2.3-1a7 7 0 0 0 2.6 1.5L11 22h4l.4-3.5a7 7 0 0 0 2.6-1.5l2.3 1 2-3.5-2-1.5c.1-.5.2-1 .2-1.5Z",
  play: "M8 5v14l11-7L8 5Z",
  folder: "M4 7h6l2 2h8v10H4V7Z",
  spark: "M12 2 9 9 2 12l7 3 3 7 3-7 7-3-7-3-3-7Z",
};
</script>

<template>
  <svg
    class="ui-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name]" />
  </svg>
</template>

<style scoped>
.ui-icon {
  flex-shrink: 0;
}
</style>
