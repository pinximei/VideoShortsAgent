<script setup lang="ts">
import { ref } from "vue";
import PageHeader from "@/components/PageHeader.vue";

const licenseKey = ref("");
const status = ref("未激活 · 免费版（手动裁剪不限，AI 每月 2 次 + 水印）");
const busy = ref(false);

async function activate() {
  if (!licenseKey.value.trim()) return;
  busy.value = true;
  try {
    // await invoke("activate_license", { key: licenseKey.value.trim() });
    status.value = "演示：激活码将写入 %APPDATA%\\VideoShortsAgent\\license.dat";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="license-layout">
    <PageHeader
      title="授权"
      description="买断激活码一次购买、本机永久使用。我们不销售 Token，也不代扣 API 费用。"
    />

    <div class="split">
      <div class="card">
        <div class="field">
          <label>激活码（VSA1-…）</label>
          <input v-model="licenseKey" class="input" type="text" placeholder="VSA1-XXXX-XXXX-XXXX" />
        </div>
        <p class="status">{{ status }}</p>
        <button type="button" class="btn btn-primary" :disabled="busy" @click="activate">
          {{ busy ? "验证中…" : "激活" }}
        </button>
      </div>

      <div class="card compare">
        <h3 class="card-title">版本对比</h3>
        <table>
          <thead>
            <tr>
              <th></th>
              <th>免费</th>
              <th>专业版</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>本地裁剪 / 抖音包</td>
              <td><span class="yes">支持</span></td>
              <td><span class="yes">支持</span></td>
            </tr>
            <tr>
              <td>AI 导出</td>
              <td>2 次/月</td>
              <td>不限</td>
            </tr>
            <tr>
              <td>导出水印</td>
              <td>有</td>
              <td>无</td>
            </tr>
            <tr>
              <td>API 费用</td>
              <td colspan="2">自备 Key，自付</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status {
  font-size: 13px;
  color: var(--vsa-text-muted);
  margin: 16px 0;
}

.card-title {
  margin: 0 0 16px;
  font-size: 15px;
}

.compare table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.compare th,
.compare td {
  padding: 10px 8px;
  border-bottom: 1px solid var(--vsa-border);
  text-align: left;
}

.compare th:not(:first-child),
.compare td:not(:first-child) {
  text-align: center;
}

.compare th {
  color: var(--vsa-text-muted);
  font-weight: 600;
}

.yes {
  color: var(--vsa-success);
  font-weight: 600;
}
</style>
