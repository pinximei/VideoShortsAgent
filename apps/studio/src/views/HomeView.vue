<script setup lang="ts">
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import UiIcon from "@/components/icons/UiIcon.vue";
import type { IconName } from "@/config/nav";

const router = useRouter();

const cards: {
  title: string;
  desc: string;
  path: string;
  icon: IconName;
  tag: string;
}[] = [
  {
    title: "本地裁剪",
    desc: "按时间段切多段并合并，无需联网",
    path: "/clip",
    icon: "clip",
    tag: "免费",
  },
  {
    title: "抖音发布包",
    desc: "9:16 竖屏 + 时长校验，一键出片",
    path: "/douyin",
    icon: "douyin",
    tag: "免费",
  },
  {
    title: "电商切片",
    desc: "多段商品讲解，手动标时间点",
    path: "/ecommerce",
    icon: "shop",
    tag: "免费",
  },
  {
    title: "AI 智能切片",
    desc: "需自备 DeepSeek / 其他 API Key",
    path: "/ai",
    icon: "ai",
    tag: "即将",
  },
];

const stats = [
  { label: "本地处理", value: "100%" },
  { label: "API 托管", value: "0" },
  { label: "买断起价", value: "¥5" },
];
</script>

<template>
  <div>
    <PageHeader
      title="工作台"
      description="选择场景开始剪辑。v1 主打本地裁剪与抖音包；AI 能力在设置中填写 Key 后逐步开放。"
    />

    <div class="hero card">
      <div class="hero-copy">
        <p class="eyebrow">VideoShorts Studio</p>
        <h3 class="hero-title page-title">本地剪辑，一键出片</h3>
        <p class="hero-desc">买断制桌面工具 · 不托管你的 API · 视频在本地处理</p>
        <div class="stats">
          <div v-for="s in stats" :key="s.label" class="stat">
            <span class="stat-value">{{ s.value }}</span>
            <span class="stat-label">{{ s.label }}</span>
          </div>
        </div>
      </div>
      <button type="button" class="btn btn-primary hero-cta" @click="router.push('/clip')">
        <UiIcon name="play" :size="18" />
        开始裁剪
      </button>
    </div>

    <div class="grid">
      <button
        v-for="c in cards"
        :key="c.path"
        type="button"
        class="scene card"
        @click="router.push(c.path)"
      >
        <span class="scene-icon-wrap">
          <UiIcon :name="c.icon" :size="24" />
        </span>
        <div class="scene-body">
          <div class="scene-head">
            <strong>{{ c.title }}</strong>
            <span class="scene-tag">{{ c.tag }}</span>
          </div>
          <p>{{ c.desc }}</p>
        </div>
      </button>
    </div>

    <div class="alert alert-info foot">
      专业版解锁：无水印、AI 导出次数不限。在「授权」页输入 VSA1- 开头的激活码。
    </div>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
  background: linear-gradient(135deg, var(--vsa-surface) 0%, rgba(99, 102, 241, 0.08) 100%);
  box-shadow: var(--vsa-shadow-md);
  border-color: rgba(99, 102, 241, 0.2);
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--vsa-accent);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.hero-title {
  margin: 0 0 8px;
  font-size: 24px;
}

.hero-desc {
  margin: 0 0 20px;
  color: var(--vsa-text-muted);
}

.stats {
  display: flex;
  gap: 24px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--vsa-text);
}

.stat-label {
  font-size: 12px;
  color: var(--vsa-text-faint);
}

.hero-cta {
  flex-shrink: 0;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.scene {
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}

.scene:hover {
  border-color: rgba(99, 102, 241, 0.5);
  transform: translateY(-4px);
  box-shadow: var(--vsa-shadow-md);
}

.scene-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: var(--vsa-radius-sm);
  background: var(--vsa-primary-dim);
  color: var(--vsa-primary-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.scene-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.scene-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--vsa-surface-3);
  color: var(--vsa-text-muted);
}

.scene-body p {
  margin: 0;
  font-size: 13px;
  color: var(--vsa-text-muted);
  line-height: 1.5;
}

.foot {
  margin-top: 28px;
}
</style>
