<template>
  <div>
    <div class="toolbar">
      <el-radio-group v-model="filterStatus" @change="loadTickets">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="open">待处理</el-radio-button>
        <el-radio-button value="in_progress">处理中</el-radio-button>
        <el-radio-button value="resolved">已解决</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="dialogVisible = true" style="margin-left:auto">新建工单</el-button>
    </div>

    <el-table :data="tickets" style="margin-top:16px">
      <el-table-column prop="id" label="工单号" width="100">
        <template #default="{ row }">{{ row.id?.slice(-8) }}</template>
      </el-table-column>
      <el-table-column prop="summary" label="摘要" min-width="200" show-overflow-tooltip />
      <el-table-column prop="priority" label="优先级" width="80">
        <template #default="{ row }">
          <el-tag :type="row.priority === 'urgent' ? 'danger' : row.priority === 'high' ? 'warning' : 'info'" size="small">{{ row.priority }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'open' ? 'danger' : row.status === 'in_progress' ? 'warning' : 'success'" size="small">{{ {open:'待处理',in_progress:'处理中',resolved:'已解决',closed:'已关闭'}[row.status] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="agent_id" label="坐席" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ row.created_at?.slice(0,19) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button text size="small" @click="openDetail(row)">详情</el-button>
          <el-button v-if="row.status === 'open'" text size="small" type="primary" @click="assignTicket(row)">接手</el-button>
          <el-button v-if="row.status === 'in_progress'" text size="small" type="success" @click="resolveTicket(row)">解决</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建工单 Dialog -->
    <el-dialog v-model="dialogVisible" title="新建工单" width="500px">
      <el-form :model="newTicket" label-width="80px">
        <el-form-item label="用户ID"><el-input v-model="newTicket.user_id" /></el-form-item>
        <el-form-item label="优先级"><el-select v-model="newTicket.priority"><el-option label="中" value="medium" /><el-option label="高" value="high" /><el-option label="紧急" value="urgent" /></el-select></el-form-item>
        <el-form-item label="摘要"><el-input v-model="newTicket.summary" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTicket" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

const tickets = ref([])
const filterStatus = ref('')
const dialogVisible = ref(false)
const creating = ref(false)
const newTicket = ref({ user_id: '', priority: 'medium', summary: '' })

async function loadTickets() {
  const params = { tenant_id: 'default', limit: 100 }
  if (filterStatus.value) params.status = filterStatus.value
  const resp = await client.get('/api/v1/tickets', { params })
  tickets.value = resp.data.tickets || []
}
loadTickets()

async function createTicket() {
  creating.value = true
  try {
    await client.post('/api/v1/tickets', { ...newTicket.value, tenant_id: 'default' })
    ElMessage.success('工单已创建')
    dialogVisible.value = false
    loadTickets()
  } finally { creating.value = false }
}

async function assignTicket(row) {
  await client.patch(`/api/v1/tickets/${row.id}`, { status: 'in_progress', agent_id: 'admin' })
  ElMessage.success('已接手')
  loadTickets()
}

async function resolveTicket(row) {
  const { value } = await ElMessageBox.prompt('处理备注', '解决工单')
  if (value !== null) {
    await client.patch(`/api/v1/tickets/${row.id}`, { status: 'resolved', resolution_note: value })
    ElMessage.success('已解决')
    loadTickets()
  }
}

function openDetail(row) {
  ElMessageBox.alert(`摘要: ${row.summary}\n状态: ${row.status}\n坐席: ${row.agent_id || '未分配'}\n备注: ${row.resolution_note || '无'}`, '工单详情')
}
</script>

<style scoped>
.toolbar { display: flex; align-items: center; }
</style>
