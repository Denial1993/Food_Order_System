<script setup lang="ts">
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-bold">桌位管理</h1>
    <div class="card text-sm text-slate-500">
      <p class="mb-2 font-medium text-slate-700">狀態機:IDLE → ORDERING → (PAID) → CLEANING → IDLE</p>
      <p>TODO: 桌位卡片網格,點擊「開桌」呼叫 <code>POST /api/tables/{table_no}/open</code></p>
    </div>
  </div>
</template>
