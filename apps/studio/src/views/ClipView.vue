<script setup lang="ts">
import PageHeader from "@/components/PageHeader.vue";
import ExportWorkbench from "@/components/ExportWorkbench.vue";
</script>

<template>
  <div>
    <PageHeader
      title="本地裁剪"
      description="输入多段时间点，合并导出为一个 MP4。完全离线，适合长视频拆条。"
    />
    <ExportWorkbench mode="clip">
      <template #tips>
        <li>时间格式支持 分:秒 或纯秒数</li>
        <li>多段将按顺序拼接</li>
      </template>
    </ExportWorkbench>
  </div>
</template>
