<script setup lang="ts"></script>

<template>
  <div class="space-y-4">
    <h1 class="text-2xl font-bold">系統參數</h1>
    <div class="card text-sm text-slate-500 space-y-2">
      <p>表結構參考 Pet_Dev_PI.dbo.tblsysCode:</p>
      <pre class="bg-slate-50 p-3 rounded text-xs overflow-auto">CodeID / CodeNo / CodeType / CodeStr / CodeValue / RoleID
CodeDesc / CodeSeq / StatusCode + AddUser/AddDate/AddIpAddr/UpdUser/UpdDate/UpdIpAddr</pre>
      <p>常用鍵:</p>
      <ul class="list-disc pl-5">
        <li><code>SERVICE_FEE_RATE</code> — 服務費率 (例 0.10 = 10%)</li>
        <li><code>BUSINESS_STATUS</code> — 營業狀態 (OPEN / CLOSE)</li>
      </ul>
      <p>TODO: 串接 /api/admin/system-config CRUD</p>
    </div>
  </div>
</template>
