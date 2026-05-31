<script setup lang="ts">
import { useRoute } from "vue-router";
import { navItems } from "@/config/nav";
import UiIcon from "@/components/icons/UiIcon.vue";

const route = useRoute();

const mainItems = navItems.filter((i) => i.section === "main");
const aiItems = navItems.filter((i) => i.section === "ai");
const sysItems = navItems.filter((i) => i.section === "system");
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="brand-mark">
        <UiIcon name="spark" :size="18" />
      </span>
      <div>
        <div class="brand-title">VideoShorts</div>
        <div class="brand-sub">Studio</div>
      </div>
    </div>

    <nav class="nav">
      <div class="nav-section">视频</div>
      <router-link
        v-for="item in mainItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'nav-item--active': route.path === item.path }"
      >
        <UiIcon :name="item.icon" :size="18" class="nav-icon" />
        <span>{{ item.label }}</span>
      </router-link>

      <div class="nav-section">AI · 需 Key</div>
      <router-link
        v-for="item in aiItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'nav-item--active': route.path === item.path }"
      >
        <UiIcon :name="item.icon" :size="18" class="nav-icon" />
        <span>{{ item.label }}</span>
        <span v-if="item.soon" class="pill">即将</span>
      </router-link>

      <div class="nav-section">系统</div>
      <router-link
        v-for="item in sysItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ 'nav-item--active': route.path === item.path }"
      >
        <UiIcon :name="item.icon" :size="18" class="nav-icon" />
        <span>{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-foot">
      <span class="badge-free">买断制 · BYOK</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--vsa-sidebar-w);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: rgba(20, 26, 36, 0.88);
  backdrop-filter: blur(16px);
  border-right: 1px solid var(--vsa-border-subtle);
  padding: 20px 12px;
  position: relative;
  z-index: 2;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 10px 24px;
}

.brand-mark {
  width: 44px;
  height: 44px;
  border-radius: var(--vsa-radius-sm);
  background: linear-gradient(135deg, var(--vsa-primary), #7c3aed);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: var(--vsa-shadow-glow);
}

.brand-title {
  font-family: var(--vsa-font-display);
  font-weight: 700;
  font-size: 16px;
  line-height: 1.2;
}

.brand-sub {
  font-size: 12px;
  color: var(--vsa-text-muted);
}

.nav-section {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--vsa-text-faint);
  padding: 12px 12px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--vsa-radius-sm);
  color: var(--vsa-text-muted);
  text-decoration: none;
  margin-bottom: 4px;
  position: relative;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: var(--vsa-surface-2);
  color: var(--vsa-text);
}

.nav-item--active {
  background: var(--vsa-primary-dim);
  color: #e0e7ff;
}

.nav-item--active::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 4px 4px 0;
  background: linear-gradient(180deg, var(--vsa-primary), var(--vsa-accent));
}

.nav-icon {
  opacity: 0.95;
}

.pill {
  margin-left: auto;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--vsa-surface-3);
  color: var(--vsa-text-faint);
}

.sidebar-foot {
  margin-top: auto;
  padding: 16px 12px 8px;
}
</style>
