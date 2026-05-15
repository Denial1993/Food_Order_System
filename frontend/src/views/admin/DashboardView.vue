<script setup lang="ts">
const stats = [
  { label: '今日營收', value: 'NT$ 0' },
  { label: '在線桌數', value: '0' },
  { label: '待處理訂單', value: '0' },
  { label: '今日訂單數', value: '0' },
]
</script>

<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-bold">儀表板</h1>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div v-for="s in stats" :key="s.label" class="card">
        <div class="text-sm text-slate-500">{{ s.label }}</div>
        <div class="text-2xl font-bold mt-1">{{ s.value }}</div>
      </div>
    </div>
    <div class="card text-sm text-slate-500">TODO: 串接 /api/admin/dashboard</div>
  </div>
</template>
