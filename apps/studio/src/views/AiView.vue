<script setup lang="ts">
import { useRouter } from "vue-router";
import PageHeader from "@/components/PageHeader.vue";
import UiIcon from "@/components/icons/UiIcon.vue";

const router = useRouter();
</script>

<template>
  <div>
    <PageHeader
      title="AI 智能切片"
      description="根据字幕/语音自动找高光片段。需你在设置中填写 API Key，费用由你直接向厂商支付。"
    />

    <div class="card placeholder">
      <div class="icon-wrap">
        <UiIcon name="ai" :size="40" />
      </div>
      <h3>即将在 Tauri 版接入</h3>
      <p>
        当前 Python 版已支持 BYOK 流程。桌面版将复用相同逻辑：读取本地视频，调用你的
        DeepSeek / OpenAI 兼容接口，生成时间段建议后一键导出。
      </p>
      <div class="badges">
        <span class="badge badge-key">需要 API Key</span>
        <span class="badge badge-free">免费版每月 2 次 AI 导出</span>
      </div>
      <button type="button" class="btn btn-primary" @click="router.push('/settings')">
        去设置 Key
      </button>
    </div>
  </div>
</template>

<style scoped>
.placeholder {
  max-width: 520px;
  margin: 0 auto;
  text-align: center;
  padding: 48px 32px;
  box-shadow: var(--vsa-shadow-md);
}

.icon-wrap {
  width: 72px;
  height: 72px;
  margin: 0 auto 20px;
  border-radius: var(--vsa-radius);
  background: var(--vsa-primary-dim);
  color: var(--vsa-primary-hover);
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder h3 {
  margin: 0 0 12px;
  font-size: 20px;
}

.placeholder p {
  color: var(--vsa-text-muted);
  margin: 0 0 24px;
  line-height: 1.6;
}

.badges {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}
</style>
