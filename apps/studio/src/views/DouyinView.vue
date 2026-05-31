<script setup lang="ts">
import PageHeader from "@/components/PageHeader.vue";
import ExportWorkbench from "@/components/ExportWorkbench.vue";
</script>

<template>
  <div>
    <PageHeader
      title="抖音发布包"
      description="自动 9:16 竖屏裁切，并校验总时长（默认 ≤60s），适合短视频直发。"
    />
    <ExportWorkbench mode="douyin" :default-vertical="true" :max-duration-sec="60">
      <template #alert>
        <div class="alert alert-warn">导出前会检测总时长；超出上限将提示分段或缩短。</div>
      </template>
      <template #tips>
        <li>建议源视频主体居中，裁切损失更小</li>
        <li>可配合「本地裁剪」先粗剪再竖屏</li>
      </template>
    </ExportWorkbench>
  </div>
</template>
