<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { navItems } from "@/config/nav";
import SidebarNav from "@/components/SidebarNav.vue";
import TopBar from "@/components/TopBar.vue";

const route = useRoute();
const pageTitle = computed(
  () => navItems.find((i) => i.path === route.path)?.label ?? "VideoShorts Studio",
);
</script>

<template>
  <div class="shell">
    <div class="ambient" aria-hidden="true">
      <div class="orb orb-a" />
      <div class="orb orb-b" />
    </div>
    <SidebarNav />
    <div class="shell-main">
      <TopBar :title="pageTitle" />
      <main class="shell-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100%;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.ambient {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
}

.orb-a {
  width: 420px;
  height: 420px;
  background: radial-gradient(circle, #6366f1 0%, transparent 70%);
  top: -120px;
  right: 10%;
}

.orb-b {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, #7c3aed 0%, transparent 70%);
  bottom: -80px;
  left: 20%;
}

.shell-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.shell-content {
  flex: 1;
  overflow: auto;
  padding: 24px 32px 40px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
