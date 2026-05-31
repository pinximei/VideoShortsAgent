<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";

const deepseekKey = ref("");
const openaiBase = ref("https://api.deepseek.com");
const ffmpegPath = ref("");
const outputDir = ref("");
const saved = ref(false);

async function save() {
  saved.value = false;
  try {
    // await invoke("save_user_settings", { ... });
    saved.value = true;
  } catch {
    saved.value = true; // demo in browser
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="设置"
      description="密钥仅保存在本机 %APPDATA%\VideoShortsAgent\，不会上传到我们服务器。"
    />

    <div class="alert alert-info" style="margin-bottom: 20px">
      方案 A：我们只卖软件。AI 相关功能使用<strong>你自己的</strong> API Key，用量与账单由厂商直接对你结算。
    </div>

    <div class="card section">
      <h3 class="section-title">AI（BYOK）</h3>
      <div class="field">
        <label>DeepSeek / 兼容 API Key</label>
        <input v-model="deepseekKey" class="input" type="password" placeholder="sk-…" autocomplete="off" />
      </div>
      <div class="field">
        <label>API Base URL（可选）</label>
        <input v-model="openaiBase" class="input" type="url" />
      </div>
    </div>

    <div class="card section">
      <h3 class="section-title">FFmpeg 与输出</h3>
      <div class="field">
        <label>FFmpeg 路径（留空则使用 PATH 或内置 bin）</label>
        <input v-model="ffmpegPath" class="input" type="text" placeholder="C:\ffmpeg\bin\ffmpeg.exe" />
      </div>
      <div class="field">
        <label>默认输出目录</label>
        <input v-model="outputDir" class="input" type="text" placeholder="C:\Users\你\Videos\VideoShorts" />
      </div>
    </div>

    <div class="actions">
      <button type="button" class="btn btn-primary" @click="save">保存设置</button>
      <span v-if="saved" class="saved">已保存（演示）</span>
    </div>
  </div>
</template>

<style scoped>
.section {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 16px;
  font-size: 15px;
}

.field {
  margin-bottom: 14px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.saved {
  font-size: 13px;
  color: var(--vsa-success);
}
</style>
