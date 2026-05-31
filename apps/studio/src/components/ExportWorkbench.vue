<script setup lang="ts">
import { ref, watch } from "vue";
import { runExport } from "@/composables/useExport";
import ProgressBar from "@/components/ProgressBar.vue";
import UiIcon from "@/components/icons/UiIcon.vue";

const props = defineProps<{
  mode: "clip" | "douyin" | "ecommerce";
  defaultVertical?: boolean;
  maxDurationSec?: number;
}>();

const videoPath = ref("");
const segments = ref("0:00-0:30\n0:45-1:15");
const vertical = ref(props.defaultVertical ?? false);
const status = ref("就绪。选择视频并填写时间段后点击导出。");
const statusKind = ref<"idle" | "busy" | "ok" | "err">("idle");
const busy = ref(false);
const lastOutput = ref("");
const progress = ref(0);

watch(busy, (v) => {
  if (!v) progress.value = 0;
});

async function pickVideo() {
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selected = await open({
      multiple: false,
      filters: [{ name: "视频", extensions: ["mp4", "mkv", "mov", "webm"] }],
    });
    if (selected && typeof selected === "string") {
      videoPath.value = selected;
      status.value = "已选择视频，请填写时间段后导出。";
      statusKind.value = "idle";
    }
  } catch {
    status.value = "浏览器预览：请手动输入视频路径（Tauri 内可用浏览按钮）";
  }
}

async function onExport() {
  if (!videoPath.value.trim()) {
    status.value = "请先选择或填写视频路径";
    statusKind.value = "err";
    return;
  }
  busy.value = true;
  statusKind.value = "busy";
  progress.value = 12;
  status.value = "正在解析时间段…";
  const tick = window.setInterval(() => {
    if (progress.value < 88) progress.value += 8;
  }, 200);
  try {
    progress.value = 40;
    status.value = "FFmpeg 处理中…";
    const res = await runExport({
      videoPath: videoPath.value.trim(),
      segments: segments.value,
      vertical: vertical.value,
      mode: props.mode,
    });
    progress.value = 100;
    status.value = res.message;
    statusKind.value = res.output_path ? "ok" : "idle";
    if (res.output_path) lastOutput.value = res.output_path;
  } catch (e) {
    status.value = e instanceof Error ? e.message : String(e);
    statusKind.value = "err";
  } finally {
    window.clearInterval(tick);
    busy.value = false;
  }
}

async function openOutputFolder() {
  if (!lastOutput.value) return;
  try {
    await import("@/composables/useTauri").then(({ tauriInvoke }) =>
      tauriInvoke("open_output_folder", { path: lastOutput.value }),
    );
  } catch {
    status.value = "无法打开文件夹（仅桌面版可用）";
    statusKind.value = "err";
  }
}
</script>

<template>
  <div class="split">
    <div class="stack">
      <slot name="alert" />

      <div class="card steps">
        <span class="step" :class="{ on: videoPath }">1 素材</span>
        <span class="step-line" />
        <span class="step" :class="{ on: segments.trim() }">2 时间轴</span>
        <span class="step-line" />
        <span class="step" :class="{ on: busy || lastOutput }">3 导出</span>
      </div>

      <div class="card">
        <div class="field">
          <label>视频文件</label>
          <div class="row">
            <input v-model="videoPath" class="input" type="text" placeholder="C:\Videos\input.mp4" />
            <button type="button" class="btn btn-secondary" @click="pickVideo">浏览</button>
          </div>
        </div>

        <div class="field field-gap">
          <label>时间段（每行一段，如 0:30-1:05 或 90-120）</label>
          <textarea v-model="segments" class="textarea" rows="7" />
        </div>

        <label v-if="mode !== 'douyin'" class="check">
          <input v-model="vertical" type="checkbox" />
          导出为 9:16 竖屏
        </label>
        <p v-else class="hint">抖音模式将自动使用 9:16 竖屏，总时长上限 {{ maxDurationSec ?? 60 }} 秒。</p>

        <button
          type="button"
          class="btn btn-primary export-btn"
          :disabled="busy"
          @click="onExport"
        >
          {{ busy ? "处理中…" : "开始导出" }}
        </button>
      </div>
    </div>

    <div class="stack">
      <div class="card preview-card">
        <h3 class="card-title">输出与日志</h3>
        <ProgressBar v-if="busy || progress === 100" :value="progress" label="导出进度" />
        <p class="status" :class="statusKind">{{ status }}</p>
        <div class="preview-placeholder">
          <UiIcon v-if="!lastOutput" name="play" :size="32" />
          <template v-else>
            <UiIcon name="folder" :size="28" />
            <small class="path">{{ lastOutput }}</small>
          </template>
        </div>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="!lastOutput"
          @click="openOutputFolder"
        >
          <UiIcon name="folder" :size="16" />
          打开输出文件夹
        </button>
      </div>

      <div class="card tips">
        <h3 class="card-title">提示</h3>
        <ul>
          <li>本功能<strong>不需要</strong> API Key，本地 FFmpeg 处理</li>
          <li>请确保已安装 FFmpeg 或随包附带 bin 目录</li>
          <slot name="tips" />
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.steps {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px;
}

.step {
  font-size: 12px;
  font-weight: 600;
  color: var(--vsa-text-faint);
  transition: color 0.15s ease;
}

.step.on {
  color: var(--vsa-primary-hover);
}

.step-line {
  flex: 1;
  height: 1px;
  background: var(--vsa-border);
  max-width: 48px;
}

.row {
  display: flex;
  gap: 8px;
}

.row .input {
  flex: 1;
}

.field-gap {
  margin-top: 16px;
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  color: var(--vsa-text-muted);
  font-size: 13px;
}

.hint {
  margin: 12px 0;
  font-size: 13px;
  color: var(--vsa-warn);
}

.export-btn {
  width: 100%;
  margin-top: 8px;
}

.card-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 650;
}

.status {
  font-size: 13px;
  color: var(--vsa-text-muted);
  margin: 0 0 16px;
  min-height: 2.5em;
}

.status.ok {
  color: var(--vsa-success);
}

.status.err {
  color: var(--vsa-danger);
}

.status.busy {
  color: var(--vsa-accent);
}

.preview-placeholder {
  height: 200px;
  border-radius: var(--vsa-radius-sm);
  border: 1px dashed var(--vsa-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--vsa-text-muted);
  margin-bottom: 16px;
  background: var(--vsa-surface-2);
}

.path {
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.tips ul {
  margin: 0;
  padding-left: 18px;
  color: var(--vsa-text-muted);
  font-size: 13px;
}

.tips li {
  margin-bottom: 8px;
}
</style>
