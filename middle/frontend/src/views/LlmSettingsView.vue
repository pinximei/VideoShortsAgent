<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type LlmSettings } from "../api";

const form = ref({
  api_key: "",
  base_url: "https://api.deepseek.com/v1",
  model: "deepseek-chat",
  enabled: true,
});
const info = ref<LlmSettings | null>(null);
const err = ref("");
const okMsg = ref("");
const testing = ref(false);
const saving = ref(false);

async function load() {
  try {
    info.value = await api.llmSettings();
    form.value.base_url = info.value.base_url || form.value.base_url;
    form.value.model = info.value.model || form.value.model;
    form.value.enabled = info.value.enabled ?? true;
    err.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

async function save() {
  saving.value = true;
  okMsg.value = "";
  err.value = "";
  try {
    info.value = await api.saveLlmSettings({
      api_key: form.value.api_key || undefined,
      base_url: form.value.base_url,
      model: form.value.model,
      enabled: form.value.enabled,
    });
    form.value.api_key = "";
    okMsg.value = "已保存到本地 .env（并更新 config.yaml 中的 llm.enabled）";
    await load();
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}

async function testConn() {
  testing.value = true;
  okMsg.value = "";
  err.value = "";
  try {
    const r = await api.testLlmSettings();
    okMsg.value = `连通成功：model=${r.model}，返回 ${JSON.stringify(r.sample)}`;
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  } finally {
    testing.value = false;
  }
}

onMounted(load);
</script>

<template>
  <h1>DeepSeek 编排</h1>
  <p class="lead">
    用于生成口播分镜、每段 <code>tts_text</code>、字幕样式与转场参数。配音与 Remotion 渲染仍在本地执行。
  </p>

  <div v-if="info" class="account-card" style="margin-bottom: 1rem">
    <p>
      Key 状态：
      <strong>{{ info.api_key_set ? "已配置" : "未配置" }}</strong>
      <span v-if="info.api_key_masked" class="muted">（{{ info.api_key_masked }}）</span>
    </p>
    <p class="muted">写入路径：{{ info.env_path }}</p>
  </div>

  <div class="account-card">
    <label class="field">
      <span>DeepSeek API Key</span>
      <input
        v-model="form.api_key"
        type="password"
        placeholder="sk-...（留空则不修改已保存的 Key）"
        autocomplete="off"
      />
    </label>
    <label class="field">
      <span>API Base URL</span>
      <input v-model="form.base_url" type="text" />
    </label>
    <label class="field">
      <span>模型</span>
      <input v-model="form.model" type="text" placeholder="deepseek-chat" />
    </label>
    <label class="field" style="flex-direction: row; align-items: center; gap: 0.5rem">
      <input v-model="form.enabled" type="checkbox" />
      <span>启用 LLM 分镜（llm.enabled）</span>
    </label>

    <div class="row-actions" style="margin-top: 1rem">
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? "保存中…" : "保存配置" }}
      </button>
      <button class="btn btn-ghost" :disabled="testing" @click="testConn">
        {{ testing ? "测试中…" : "测试连通" }}
      </button>
      <button class="btn btn-ghost" @click="load">刷新</button>
    </div>
  </div>

  <p v-if="okMsg" style="color: #86efac; margin-top: 1rem">{{ okMsg }}</p>
  <p v-if="err" style="color: #fca5a5; margin-top: 1rem">{{ err }}</p>

  <p class="muted" style="margin-top: 1.5rem">
    获取 Key：
    <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener">platform.deepseek.com</a>
  </p>
</template>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.85rem;
}
.field input[type="text"],
.field input[type="password"] {
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border, #334155);
  background: var(--input-bg, #0f172a);
  color: inherit;
  font-family: inherit;
}
</style>
