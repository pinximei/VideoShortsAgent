<script setup lang="ts">
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import UiIcon from "@/components/icons/UiIcon.vue";

const router = useRouter();
</script>

<template>
  <div>
    <PageHeader
      title="翻译配音"
      description="字幕生成、翻译与 TTS 配音。同样采用 BYOK，密钥仅存本机。"
    />

    <div class="card placeholder">
      <div class="icon-wrap">
        <UiIcon name="subtitle" :size="40" />
      </div>
      <h3>功能规划中</h3>
      <p>与 AI 切片共用设置页的 Key 与 FFmpeg 管线，预计 v1.1 开放。</p>
      <button type="button" class="btn btn-secondary" @click="router.push('/settings')">
        查看 API 设置
      </button>
    </div>
  </div>
</template>

<style scoped>
.placeholder {
  max-width: 480px;
  margin: 0 auto;
  text-align: center;
  padding: 48px 32px;
}

.icon-wrap {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  border-radius: var(--vsa-radius);
  background: var(--vsa-surface-3);
  color: var(--vsa-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder p {
  color: var(--vsa-text-muted);
  margin: 0 0 24px;
}
</style>
