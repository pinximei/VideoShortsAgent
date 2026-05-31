<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type TtsSettings } from "../api";

const form = ref({
  dashscope_api_key: "",
  tts_provider: "auto",
  tts_fallback: "dashscope,azure,openai",
});
const info = ref<TtsSettings | null>(null);
const err = ref("");
const okMsg = ref("");
const testing = ref(false);
const saving = ref(false);

async function load() {
  try {
    info.value = await api.ttsSettings();
    form.value.tts_provider = info.value.tts_provider || "auto";
    form.value.tts_fallback = info.value.tts_fallback || "dashscope,azure,openai";
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
    info.value = await api.saveTtsSettings({
      dashscope_api_key: form.value.dashscope_api_key || undefined,
      tts_provider: form.value.tts_provider,
      tts_fallback: form.value.tts_fallback,
    });
    form.value.dashscope_api_key = "";
    okMsg.value = "已保存到仓库根目录 .env";
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
    const r = await api.testTtsSettings();
    const ds = r.providers?.dashscope;
    if (ds?.ok) {
      okMsg.value = `阿里云 TTS 可用（${ds.latency_sec ?? "?"}s，${ds.bytes ?? 0} bytes）`;
    } else {
      err.value = ds?.error || r.providers?.edge?.error || "探测未通过，请检查 Key 与账户余额";
    }
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  } finally {
    testing.value = false;
  }
}

onMounted(load);
</script>

<template>
  <h1>配音 · 阿里云百炼</h1>
  <p class="lead">
    Edge TTS 限流（503）时自动切换到 DashScope。Key 写入本地 <code>.env</code>，勿提交 git。
  </p>

  <div v-if="info" class="account-card" style="margin-bottom: 1rem">
    <p>
      阿里云 Key：
      <strong>{{ info.dashscope_api_key_set ? "已配置" : "未配置" }}</strong>
      <span v-if="info.dashscope_api_key_masked" class="muted">（{{ info.dashscope_api_key_masked }}）</span>
    </p>
    <p class="muted">环境变量：{{ info.dashscope_api_key_env }} · 写入 {{ info.env_path }}</p>
  </div>

  <div class="account-card">
    <label class="field">
      <span>DashScope API Key（阿里云百炼）</span>
      <input
        v-model="form.dashscope_api_key"
        type="password"
        placeholder="sk-...（留空则不修改已保存的 Key）"
        autocomplete="off"
      />
    </label>
    <label class="field">
      <span>TTS 策略（TTS_PROVIDER）</span>
      <select v-model="form.tts_provider">
        <option value="auto">auto — Edge 优先，失败走 Key 备用</option>
        <option value="edge">edge — 仅 Edge（免费）</option>
        <option value="dashscope">dashscope — 仅阿里云</option>
      </select>
    </label>
    <label class="field">
      <span>备用顺序（TTS_FALLBACK）</span>
      <input v-model="form.tts_fallback" type="text" placeholder="dashscope,azure,openai" />
    </label>

    <div class="row-actions" style="margin-top: 1rem">
      <button class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? "保存中…" : "保存配置" }}
      </button>
      <button class="btn btn-ghost" :disabled="testing" @click="testConn">
        {{ testing ? "测试中…" : "测试阿里云 TTS" }}
      </button>
      <button class="btn btn-ghost" @click="load">刷新</button>
    </div>
  </div>

  <p v-if="okMsg" style="color: #86efac; margin-top: 1rem">{{ okMsg }}</p>
  <p v-if="err" style="color: #fca5a5; margin-top: 1rem">{{ err }}</p>

  <p class="muted" style="margin-top: 1.5rem">
    开通 Key：
    <a :href="info?.help_url || 'https://bailian.console.aliyun.com/'" target="_blank" rel="noopener">
      阿里云百炼控制台
    </a>
    （语音合成需账户有余额，欠费会返回 Arrearage）
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
.field input[type="password"],
.field select {
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid var(--border, #334155);
  background: var(--input-bg, #0f172a);
  color: inherit;
  font-family: inherit;
}
</style>
