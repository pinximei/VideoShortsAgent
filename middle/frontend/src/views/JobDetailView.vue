<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { api, type Theme } from "../api";

const route = useRoute();
const id = computed(() => Number(route.params.id));
const job = ref<Record<string, unknown> | null>(null);
const themes = ref<Theme[]>([]);
const scriptText = ref("");
const err = ref("");
const msg = ref("");

const channels = [
  { id: "douyin", label: "抖音" },
  { id: "xhs", label: "小红书" },
  { id: "toutiao", label: "今日头条" },
  { id: "douban", label: "豆瓣" },
];

async function load() {
  try {
    job.value = await api.job(id.value);
    const arts = (job.value?.artifacts as { path: string; url: string }[]) || [];
    const script = arts.find((a) => a.path === "script.txt");
    scriptText.value = "";
    if (script) {
      const r = await fetch(script.url);
      scriptText.value = await r.text();
    }
    err.value = "";
    msg.value = "";
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

async function mark(ch: string) {
  try {
    await api.publish(id.value, ch);
    msg.value = `已标记发布：${ch}`;
    await load();
  } catch (e) {
    msg.value = e instanceof Error ? e.message : String(e);
  }
}

async function changeTheme(themeId: string) {
  try {
    await api.patchTheme(id.value, themeId);
    msg.value = "赛道已更新";
    await load();
  } catch (e) {
    msg.value = e instanceof Error ? e.message : String(e);
  }
}

function accountLabel(ch: string) {
  const labels = job.value?.account_labels as Record<string, string> | undefined;
  return labels?.[ch] || channels.find((c) => c.id === ch)?.label || ch;
}

function publishFile(ch: string) {
  const map: Record<string, string> = {
    douyin: "publish/douyin_title.txt",
    xhs: "publish/xhs_title.txt",
    toutiao: "publish/toutiao_micro.txt",
    douban: "publish/douban_note.txt",
  };
  const arts = (job.value?.artifacts as { path: string; url: string }[]) || [];
  return arts.find((a) => a.path === map[ch]);
}

onMounted(async () => {
  try {
    themes.value = await api.themes();
  } catch {
    themes.value = [];
  }
  await load();
});
</script>

<template>
  <h1>任务 #{{ id }}</h1>
  <p v-if="job" class="lead">
    状态 <span class="badge" :class="'badge-' + job.status">{{ job.status }}</span>
    <span v-if="job.theme" class="badge">赛道 · {{ (job.theme as Theme).label }}</span>
    <span v-if="job.step" class="muted"> · 步骤 {{ job.step }}</span>
    <span v-if="(job.brief_json as Record<string, unknown>)?.worth_score" class="muted">
      · worth {{ (job.brief_json as Record<string, unknown>).worth_score }}
    </span>
  </p>

  <div v-if="job?.events && (job.events as unknown[]).length" class="panel">
    <div class="panel-title">执行时间线</div>
    <ul class="file-list">
      <li v-for="(ev, i) in job.events as { step: string; status: string; message: string; created_at: string }[]" :key="i">
        <span class="muted">{{ ev.created_at }}</span>
        · {{ ev.step }} — {{ ev.message || ev.status }}
      </li>
    </ul>
  </div>

  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>
  <p v-if="msg" class="muted" style="color: #86efac">{{ msg }}</p>

  <div v-if="job && themes.length" class="panel">
    <div class="panel-title">内容赛道</div>
    <div class="row-actions">
      <select
        class="btn btn-ghost"
        :value="String(job.theme_id || '')"
        @change="changeTheme(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="t in themes" :key="t.id" :value="t.id">{{ t.label }}</option>
      </select>
      <span class="muted">一账号一类型，发错赛道请在此调整</span>
    </div>
  </div>

  <div v-if="job" class="panel">
    <div class="panel-title">发布状态（按赛道账号）</div>
    <div class="row-actions">
      <template v-for="c in channels" :key="c.id">
        <button
          class="btn btn-ghost btn-sm"
          :disabled="(job.published as Record<string, boolean>)?.[c.id]"
          @click="mark(c.id)"
        >
          {{
            (job.published as Record<string, boolean>)?.[c.id]
              ? `✓ ${accountLabel(c.id)}`
              : `标记 ${accountLabel(c.id)}`
          }}
        </button>
        <a
          v-if="publishFile(c.id)"
          :href="publishFile(c.id)!.url"
          target="_blank"
          rel="noreferrer"
          class="btn btn-ghost btn-sm"
          >文案</a
        >
      </template>
    </div>
  </div>

  <div v-if="scriptText" class="panel">
    <div class="panel-title">口播稿 script.txt</div>
    <pre class="pre">{{ scriptText }}</pre>
  </div>

  <div v-if="job?.brief_json" class="panel">
    <div class="panel-title">Video Brief</div>
    <pre class="pre">{{ JSON.stringify(job.brief_json, null, 2) }}</pre>
  </div>

  <div v-if="job?.artifacts" class="panel">
    <div class="panel-title">产出文件（点击下载/查看）</div>
    <ul class="file-list">
      <li v-for="a in job.artifacts as { path: string; url: string }[]" :key="a.path">
        <a :href="a.url" target="_blank" rel="noreferrer">{{ a.path }}</a>
      </li>
    </ul>
  </div>
</template>
