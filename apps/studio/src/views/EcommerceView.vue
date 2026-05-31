<script setup lang="ts">
import PageHeader from "@/components/PageHeader.vue";
import ExportWorkbench from "@/components/ExportWorkbench.vue";
</script>

<template>
  <div>
    <PageHeader
      title="电商切片"
      description="按讲解段落导出多条短视频，用于商品详情、直播间切片素材。"
    />
    <ExportWorkbench mode="ecommerce">
      <template #tips>
        <li>每行一段对应一条导出（后续版本支持批量命名）</li>
        <li>可勾选竖屏适配主图视频位</li>
      </template>
    </ExportWorkbench>
  </div>
</template>
