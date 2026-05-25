<script setup lang="ts">
import { RouterLink } from 'vue-router'

// import.meta.env.DEV = true 只在 vite dev server 時成立
// npm run build 後永遠是 false → 正式環境完全不顯示開發工具列
const isDev = import.meta.env.DEV
</script>

<template>
  <main class="min-h-full flex items-center justify-center bg-slate-50 p-6">
    <div class="max-w-sm w-full text-center space-y-8">

      <!-- Logo / 品牌 -->
      <div class="space-y-2">
        <div class="text-5xl">🍱</div>
        <h1 class="text-2xl font-bold text-slate-800">歡迎光臨</h1>
        <p class="text-slate-500 text-sm">請掃描桌位上的 QR Code 開始點餐</p>
      </div>

      <!-- QR Code 圖示提示 -->
      <div class="border-2 border-dashed border-slate-200 rounded-2xl p-8 space-y-3">
        <svg class="w-16 h-16 mx-auto text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z" />
        </svg>
        <p class="text-slate-400 text-sm">用手機相機對準桌上的 QR Code</p>
      </div>

      <!-- ── 開發模式專用（正式環境不顯示）──────────────────── -->
      <div v-if="isDev" class="border border-amber-200 bg-amber-50 rounded-xl p-4 space-y-3">
        <p class="text-xs font-semibold text-amber-700 uppercase tracking-wide">
          開發模式 — 僅本機可見
        </p>
        <div class="flex flex-col gap-2">
          <RouterLink
            to="/order?table=1"
            class="btn-primary text-sm"
          >
            模擬掃碼：桌號 1
          </RouterLink>
          <RouterLink
            to="/admin"
            class="btn-ghost text-sm"
          >
            店家後台管理
          </RouterLink>
        </div>
      </div>
      <!-- ──────────────────────────────────────────────────── -->

    </div>
  </main>
</template>
