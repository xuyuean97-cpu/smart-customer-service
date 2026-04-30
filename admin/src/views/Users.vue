<template>
  <el-card>
    <template #header>用户列表</template>
    <el-table :data="users" max-height="500">
      <el-table-column prop="user_id" label="用户ID" width="200" show-overflow-tooltip />
      <el-table-column prop="conversation_count" label="对话数" width="100" />
      <el-table-column prop="avg_quality" label="平均质量" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="viewProfile(row)">画像</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import client from '../api/client'

const users = ref([])

onMounted(async () => {
  const resp = await client.get('/api/v1/admin/dashboard/users/top?limit=50')
  users.value = resp.data.users || []
})

async function viewProfile(row) {
  try {
    const resp = await client.get(`/memory/v1/profile/${row.user_id}`)
    ElMessageBox.alert(JSON.stringify(resp.data, null, 2), `${row.user_id} 用户画像`)
  } catch {
    ElMessageBox.alert('暂无画像数据', `${row.user_id}`)
  }
}
</script>
