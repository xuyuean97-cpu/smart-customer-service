<template>
  <div>
    <el-card>
      <el-form :inline="true">
        <el-form-item label="用户ID"><el-input v-model="filters.user_id" placeholder="可选" clearable style="width:160px" /></el-form-item>
        <el-form-item label="租户"><el-input v-model="filters.tenant_id" disabled style="width:120px" /></el-form-item>
        <el-form-item><el-button type="primary" @click="loadHistory" icon="Search">查询</el-button></el-form-item>
      </el-form>
    </el-card>
    <el-card style="margin-top:16px">
      <el-table :data="conversations" max-height="500">
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ (row.metadata?.created_at || row.created_at || '').slice(0,19) }}</template>
        </el-table-column>
        <el-table-column label="用户" width="110">
          <template #default="{ row }">{{ row.metadata?.user_id || row.user_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="问题" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.metadata?.data || row.data || row.content || '-' }}</template>
        </el-table-column>
        <el-table-column label="回复" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.metadata?.response || row.response || '-' }}</template>
        </el-table-column>
        <el-table-column prop="quality_score" label="质量" width="70" />
        <el-table-column label="审批" width="70">
          <template #default="{ row }">{{ row.metadata?.user_approved ? '已赞' : '-' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import client from '../api/client'

const conversations = ref([])
const filters = reactive({ tenant_id: 'default', user_id: '' })

async function loadHistory() {
  const params = { tenant_id: filters.tenant_id, limit: 100 }
  if (filters.user_id) params.user_id = filters.user_id
  const resp = await client.get('/api/v1/admin/dashboard/performance', { params: { tenant_id: 'default' } })
  try {
    const mem = await client.get('/api/v1/admin/dashboard/overview', { params: { tenant_id: 'default' } })
    // Use memory API for detailed history
    const histResp = await fetch(`/memory/v1/conversations/history?limit=50`)
    conversations.value = await histResp.json() || []
  } catch {
    conversations.value = []
  }
}
loadHistory()
</script>
