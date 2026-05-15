<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <main class="min-h-full flex items-center justify-center p-6">
    <div class="max-w-md w-full text-center space-y-6">
      <h1 class="text-3xl font-bold text-brand-600">Food Order System</h1>
      <p class="text-slate-600">QR Code 手機點餐系統 — 開發骨架</p>

      <div class="grid gap-3">
        <RouterLink to="/order?table=1" class="btn-primary">前台:模擬掃碼點餐 (桌號 1)</RouterLink>
        <RouterLink to="/admin" class="btn-ghost">後台:店家管理</RouterLink>
      </div>

      <p class="text-xs text-slate-400 pt-4">
        本機開發:後端 <code>uvicorn main:app --reload</code>,DB 由 <code>docker-compose up -d</code> 啟動
      </p>
    </div>
  </main>
</template>
