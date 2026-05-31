<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, type ChannelAccount, type ChannelConfigOverview, type PlatformChannel, type Site } from "../api";

const overview = ref<ChannelConfigOverview | null>(null);
const selectedSite = ref("");
const selectedChannel = ref("douyin");
const cards = ref<ChannelAccount[]>([]);
const err = ref("");
const ok = ref("");
const saving = ref(false);
const loginMsg = ref("");

const sites = computed(() => overview.value?.sites || []);
const channels = computed(() => overview.value?.channels || []);

const currentSite = computed(() => sites.value.find((s) => s.code === selectedSite.value));
const currentChannel = computed(() =>
  channels.value.find((c) => c.id === selectedChannel.value)
);

function emptyCard(siteCode: string, channelId: string): ChannelAccount {
  return {
    id: `tmp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    site_code: siteCode,
    channel_id: channelId,
    label: "",
    handle: "",
    profile_url: "",
    login_hint: "",
    note: "",
    enabled: true,
    is_primary: false,
  };
}

function loadCardsFromOverview() {
  if (!overview.value || !selectedSite.value || !selectedChannel.value) {
    cards.value = [];
    return;
  }
  const rows =
    overview.value.accounts_by_site_channel[selectedSite.value]?.[selectedChannel.value] || [];
  cards.value = rows.map((r) => ({ ...r }));
}

async function load() {
  err.value = "";
  try {
    overview.value = await api.channelConfig();
    if (!selectedSite.value && overview.value.sites.length) {
      selectedSite.value = overview.value.sites[0].code;
    }
    if (!selectedChannel.value && overview.value.channels.length) {
      selectedChannel.value = overview.value.channels[0].id;
    }
    loadCardsFromOverview();
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  }
}

function selectSite(site: Site) {
  selectedSite.value = site.code;
  loadCardsFromOverview();
}

function selectChannel(ch: PlatformChannel) {
  selectedChannel.value = ch.id;
  loadCardsFromOverview();
}

function addCard() {
  if (!selectedSite.value) return;
  const card = emptyCard(selectedSite.value, selectedChannel.value);
  if (!cards.value.length) card.is_primary = true;
  cards.value.push(card);
}

function removeCard(index: number) {
  cards.value.splice(index, 1);
}

function setPrimary(index: number) {
  cards.value.forEach((c, i) => {
    c.is_primary = i === index;
  });
}

async function openLogin(card: ChannelAccount) {
  loginMsg.value = "";
  if (!card.id || card.id.startsWith("tmp_")) {
    loginMsg.value = "请先保存配置，获得固定 account_id 后再登录";
    return;
  }
  if (card.channel_id !== "douyin" && card.channel_id !== "xhs") {
    loginMsg.value = "头条/豆瓣请在平台网页手工登录发文";
    return;
  }
  try {
    const res = await api.publisherOpenLogin(card.id);
    loginMsg.value = `已启动登录浏览器：${card.id}（Profile: ${(res.profile_dir as string) || "—"}）`;
  } catch (e) {
    loginMsg.value = e instanceof Error ? e.message : String(e);
  }
}

async function checkLogin(card: ChannelAccount) {
  loginMsg.value = "";
  if (!card.id || card.id.startsWith("tmp_")) {
    loginMsg.value = "请先保存配置";
    return;
  }
  if (card.channel_id !== "douyin" && card.channel_id !== "xhs") {
    return;
  }
  try {
    const res = await api.publisherLoginCheck(card.id);
    loginMsg.value = res.logged_in
      ? `✓ ${card.id} 已登录`
      : `✗ ${card.id} 未登录，请点「打开浏览器登录」`;
  } catch (e) {
    loginMsg.value = e instanceof Error ? e.message : String(e);
  }
}

async function save() {
  if (!selectedSite.value) return;
  saving.value = true;
  ok.value = "";
  err.value = "";
  try {
    const payload = cards.value.map((c, i) => ({
      ...c,
      id: c.id.startsWith("tmp_") ? "" : c.id,
      is_primary: c.is_primary || (i === 0 && !cards.value.some((x) => x.is_primary)),
    }));
    const res = await api.saveChannelAccounts(selectedSite.value, selectedChannel.value, payload);
    ok.value = `已保存 ${res.saved} 个账号到 config.yaml`;
    await load();
  } catch (e) {
    err.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <h1>渠道账号配置</h1>
  <p class="lead">
    先选<strong>站点 code</strong>（对应 Soul 网站 / 赛道），再选<strong>发布渠道</strong>，为该平台配置一个或多个账号卡片。
  </p>

  <div v-if="sites.length" class="panel">
    <div class="panel-title">1. 选择站点 code</div>
    <div class="site-grid">
      <button
        v-for="s in sites"
        :key="s.code"
        type="button"
        class="site-card"
        :class="{ 'site-card--active': s.code === selectedSite }"
        @click="selectSite(s)"
      >
        <div class="site-card__code">{{ s.code }}</div>
        <div class="site-card__label">{{ s.label }}</div>
        <div v-if="s.theme_id" class="site-card__meta muted">赛道 · {{ s.theme_id }}</div>
        <div v-if="s.base_url" class="site-card__meta muted">{{ s.base_url }}</div>
      </button>
    </div>
  </div>

  <div v-if="channels.length" class="panel">
    <div class="panel-title">2. 选择发布渠道</div>
    <div class="channel-tabs">
      <button
        v-for="ch in channels"
        :key="ch.id"
        type="button"
        class="channel-tab"
        :class="{ 'channel-tab--active': ch.id === selectedChannel }"
        @click="selectChannel(ch)"
      >
        {{ ch.label }}
        <span class="muted">· {{ ch.kind === "video" ? "视频" : "图文" }}</span>
      </button>
    </div>
  </div>

  <div v-if="currentSite && currentChannel" class="panel">
    <div class="panel-title">
      3. 账号卡片
      <span class="muted">
        {{ currentSite.label }} × {{ currentChannel.label }}
      </span>
    </div>

    <div class="row-actions">
      <button type="button" class="btn btn-ghost" @click="addCard">＋ 添加账号卡片</button>
      <button type="button" class="btn btn-primary" :disabled="saving" @click="save">
        {{ saving ? "保存中…" : "保存到配置" }}
      </button>
    </div>

    <p v-if="ok" class="muted" style="color: #86efac">{{ ok }}</p>
    <p v-if="err" class="muted" style="color: #fca5a5">{{ err }}</p>
    <p v-if="loginMsg" class="muted" style="color: #93c5fd">{{ loginMsg }}</p>

    <div v-if="cards.length" class="account-grid">
      <div v-for="(card, idx) in cards" :key="card.id" class="account-card">
        <div class="account-card__head">
          <span class="account-card__title">账号 #{{ idx + 1 }}</span>
          <label class="account-card__primary">
            <input type="radio" name="primary" :checked="card.is_primary" @change="setPrimary(idx)" />
            主账号
          </label>
        </div>

        <label class="field">
          <span>固定账号 ID（登录/发布用）</span>
          <input :value="card.id" readonly class="readonly" />
        </label>
        <label class="field">
          <span>显示名称</span>
          <input v-model="card.label" placeholder="抖音 · AI变现主号" />
        </label>
        <div
          v-if="card.channel_id === 'douyin' || card.channel_id === 'xhs'"
          class="row-actions"
          style="margin: 0.5rem 0"
        >
          <button type="button" class="btn btn-ghost btn-sm" @click="openLogin(card)">
            打开浏览器登录
          </button>
          <button type="button" class="btn btn-ghost btn-sm" @click="checkLogin(card)">
            检测登录
          </button>
        </div>
        <label class="field">
          <span>账号 ID / @handle</span>
          <input v-model="card.handle" placeholder="@your_account" />
        </label>
        <label class="field">
          <span>主页链接</span>
          <input v-model="card.profile_url" placeholder="https://..." />
        </label>
        <label class="field">
          <span>登录备注</span>
          <input v-model="card.login_hint" placeholder="手机号 / 邮箱（仅本地配置）" />
        </label>
        <label class="field">
          <span>备注</span>
          <textarea v-model="card.note" rows="2" placeholder="运营备注" />
        </label>
        <label class="field field--row">
          <input v-model="card.enabled" type="checkbox" />
          <span>启用</span>
        </label>

        <button type="button" class="btn btn-ghost btn-sm account-card__del" @click="removeCard(idx)">
          删除此卡片
        </button>
      </div>
    </div>
    <div v-else class="empty panel">暂无账号，点击「添加账号卡片」开始配置。</div>
  </div>
</template>
