<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api } from "../api";

const CHANNELS = [
  "ai-trends-news",
  "ai-trends-apps",
  "douyin",
  "xhs",
  "toutiao",
  "douban",
];

const days = ref(30);
const data = ref<Record<string, unknown> | null>(null);
const err = ref("");
const loading = ref(false);

async function load() {
  loading.value = true;
  err.value = "";
  try {
    data.value = await api.publishingStats(days.value);
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <h1>发布运营</h1>
  <p class="lead">各网站/渠道每天发了多少<strong>文章</strong>、<strong>视频</strong>，以及分类与待发布维护。</p>

  <div class="row-actions">
    <select v-model.number="days" class="btn btn-ghost" @change="load">
      <option :value="7">近 7 天</option>
      <option :value="30">近 30 天</option>
      <option :value="90">近 90 天</option>
    </select>
    <button type="button" class="btn btn-ghost" @click="load">刷新</button>
  </div>
  <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>

  <div v-if="data?.summary" class="cards">
    <div class="card highlight">
      <div class="label">今日文章</div>
      <div class="value">{{ (data.summary as Record<string, number>).today_articles }}</div>
    </div>
    <div class="card highlight">
      <div class="label">今日视频</div>
      <div class="value">{{ (data.summary as Record<string, number>).today_videos }}</div>
    </div>
    <div class="card">
      <div class="label">已打包待发</div>
      <div class="value">{{ (data.summary as Record<string, number>).packed_ready }}</div>
    </div>
  </div>

  <div v-if="data?.daily" class="panel">
    <div class="panel-title">每日各站发布（蓝条=文章，橙条=视频）</div>
    <div class="connector-daily-chart">
      <div
        v-for="row in data.daily as { date: string; sites: Record<string, { articles: number; videos: number }> }[]"
        :key="row.date"
        class="connector-daily-chart__col"
      >
        <div style="display:flex;flex-direction:column;justify-content:flex-end;height:100%;width:100%;align-items:center;gap:2px">
          <template v-for="ch in CHANNELS" :key="ch">
            <div
              v-if="row.sites[ch]?.videos"
              class="connector-daily-chart__bar"
              :style="{
                height: Math.min(55, row.sites[ch].videos * 8) + '%',
                background: 'linear-gradient(180deg,#f59e0b,#d97706)',
                maxWidth: '20px',
              }"
            />
          </template>
          <div
            class="connector-daily-chart__bar"
            :style="{
              height: Math.min(55, CHANNELS.reduce((n, ch) => n + (row.sites[ch]?.articles || 0), 0) * 4) + '%',
              maxWidth: '24px',
            }"
          />
        </div>
        <div class="connector-daily-chart__date">{{ row.date.slice(5) }}</div>
      </div>
    </div>
  </div>

  <div v-if="data?.channel_maintenance" class="panel">
    <div class="panel-title">外站维护（标记发布后计入统计）</div>
    <table>
      <thead>
        <tr>
          <th>渠道</th>
          <th>待发布</th>
          <th>最近发布</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in data.channel_maintenance as Record<string, unknown>[]" :key="String(r.channel)">
          <td>{{ r.label }}</td>
          <td>{{ r.pending }}</td>
          <td class="muted">{{ r.last_published_at || "—" }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="data?.categories" class="panel">
    <div class="panel-title">站内分类（Soul）</div>
    <ul>
      <li v-for="c in data.categories as { category: string; count: number }[]" :key="c.category">
        {{ c.category }} ({{ c.count }})
      </li>
    </ul>
  </div>

  <div v-if="data?.pipeline_categories" class="panel">
    <div class="panel-title">外站已发 · 标签分类</div>
    <ul>
      <li
        v-for="c in data.pipeline_categories as { category: string; count: number }[]"
        :key="c.category"
      >
        {{ c.category }} ({{ c.count }})
      </li>
    </ul>
  </div>
</template>
