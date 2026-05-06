<template>
  <div class="tickets-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <div class="filter-tabs">
          <button 
            v-for="status in statusOptions" 
            :key="status.value"
            :class="['filter-tab', { active: filterStatus === status.value }]"
            @click="filterStatus = status.value; loadTickets()"
          >
            {{ status.label }}
            <span v-if="status.count" class="tab-count">{{ status.count }}</span>
          </button>
        </div>
      </div>
      <div class="header-right">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input type="text" placeholder="搜索工单..." class="search-input" />
        </div>
        <button class="primary-btn" @click="dialogVisible = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建工单
        </button>
      </div>
    </div>

    <!-- Tickets Table -->
    <div class="tickets-table">
      <div class="table-header">
        <div class="th" style="width: 100px">工单号</div>
        <div class="th" style="flex: 1">摘要</div>
        <div class="th" style="width: 80px">优先级</div>
        <div class="th" style="width: 90px">状态</div>
        <div class="th" style="width: 100px">坐席</div>
        <div class="th" style="width: 160px">创建时间</div>
        <div class="th" style="width: 140px">操作</div>
      </div>
      <div class="table-body">
        <div class="table-row" v-for="ticket in tickets" :key="ticket.id">
          <div class="td" style="width: 100px">
            <span class="ticket-id">#{{ ticket.id?.slice(-8) }}</span>
          </div>
          <div class="td" style="flex: 1">
            <span class="ticket-summary">{{ ticket.summary }}</span>
          </div>
          <div class="td" style="width: 80px">
            <span :class="['priority-badge', ticket.priority]">
              {{ priorityMap[ticket.priority] || ticket.priority }}
            </span>
          </div>
          <div class="td" style="width: 90px">
            <span :class="['status-badge', ticket.status]">
              {{ statusMap[ticket.status] || ticket.status }}
            </span>
          </div>
          <div class="td" style="width: 100px">
            <span class="agent-name">{{ ticket.agent_id || '-' }}</span>
          </div>
          <div class="td" style="width: 160px">
            <span class="time-text">{{ ticket.created_at?.slice(0,16) }}</span>
          </div>
          <div class="td" style="width: 140px">
            <div class="action-btns">
              <button class="icon-action" @click="openDetail(ticket)" title="详情">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
              <button v-if="ticket.status === 'open'" class="icon-action primary" @click="assignTicket(ticket)" title="接手">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
                  <circle cx="8.5" cy="7" r="4"/>
                  <line x1="20" y1="8" x2="20" y2="14"/>
                  <line x1="23" y1="11" x2="17" y2="11"/>
                </svg>
              </button>
              <button v-if="ticket.status === 'in_progress'" class="icon-action success" @click="resolveTicket(ticket)" title="解决">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                  <polyline points="22,4 12,14.01 9,11.01"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Empty State -->
        <div v-if="!tickets.length" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
          </svg>
          <h3>暂无工单</h3>
          <p>当前筛选条件下没有工单数据</p>
        </div>
      </div>
    </div>

    <!-- New Ticket Dialog -->
    <el-dialog v-model="dialogVisible" title="新建工单" width="520px" class="custom-dialog">
      <el-form :model="newTicket" label-width="80px" class="ticket-form">
        <el-form-item label="用户ID">
          <el-input v-model="newTicket.user_id" placeholder="请输入用户ID" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="newTicket.priority" style="width: 100%">
            <el-option label="中等" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="newTicket.summary" type="textarea" :rows="4" placeholder="请输入工单摘要" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <button class="secondary-btn" @click="dialogVisible = false">取消</button>
          <button class="primary-btn" @click="createTicket" :disabled="creating">
            {{ creating ? '创建中...' : '创建工单' }}
          </button>
        </div>
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

const statusOptions = [
  { value: '', label: '全部', count: null },
  { value: 'open', label: '待处理', count: 5 },
  { value: 'in_progress', label: '处理中', count: 3 },
  { value: 'resolved', label: '已解决', count: null }
]

const priorityMap = { medium: '中', high: '高', urgent: '紧急' }
const statusMap = { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }

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
    newTicket.value = { user_id: '', priority: 'medium', summary: '' }
    loadTickets()
  } finally { 
    creating.value = false 
  }
}

async function assignTicket(row) {
  await client.patch(`/api/v1/tickets/${row.id}`, { status: 'in_progress', agent_id: 'admin' })
  ElMessage.success('已接手')
  loadTickets()
}

async function resolveTicket(row) {
  const { value } = await ElMessageBox.prompt('处理备注', '解决工单', {
    confirmButtonText: '确认解决',
    cancelButtonText: '取消'
  })
  if (value !== null) {
    await client.patch(`/api/v1/tickets/${row.id}`, { status: 'resolved', resolution_note: value })
    ElMessage.success('已解决')
    loadTickets()
  }
}

function openDetail(row) {
  ElMessageBox.alert(
    `<div style="line-height: 1.8">
      <p><strong>摘要:</strong> ${row.summary}</p>
      <p><strong>状态:</strong> ${statusMap[row.status] || row.status}</p>
      <p><strong>坐席:</strong> ${row.agent_id || '未分配'}</p>
      <p><strong>备注:</strong> ${row.resolution_note || '无'}</p>
    </div>`,
    '工单详情',
    { dangerouslyUseHTMLString: true }
  )
}
</script>

<style scoped>
.tickets-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  background: var(--bg-secondary);
  padding: 6px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.filter-tab:hover {
  color: var(--text-primary);
}

.filter-tab.active {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.tab-count {
  font-size: 11px;
  background: var(--accent-red);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.search-input {
  width: 200px;
  height: 38px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 12px 0 38px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.search-input:focus {
  border-color: var(--accent-blue);
}

.primary-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 38px;
  background: var(--accent-blue);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.primary-btn:hover {
  background: var(--accent-blue-hover);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.primary-btn svg {
  width: 16px;
  height: 16px;
}

.secondary-btn {
  padding: 0 16px;
  height: 38px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.secondary-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.tickets-table {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table-header {
  display: flex;
  padding: 12px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}

.th {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-body {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}

.table-row {
  display: flex;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  align-items: center;
  transition: background 0.15s ease;
}

.table-row:hover {
  background: var(--bg-tertiary);
}

.table-row:last-child {
  border-bottom: none;
}

.td {
  font-size: 13px;
  color: var(--text-primary);
}

.ticket-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.ticket-summary {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.priority-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.priority-badge.medium {
  background: rgba(161, 161, 170, 0.15);
  color: var(--text-secondary);
}

.priority-badge.high {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.priority-badge.urgent {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.status-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.status-badge.open {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.status-badge.in_progress {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.status-badge.resolved {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.status-badge.closed {
  background: rgba(161, 161, 170, 0.15);
  color: var(--text-muted);
}

.agent-name {
  color: var(--text-secondary);
}

.time-text {
  color: var(--text-muted);
  font-size: 12px;
}

.action-btns {
  display: flex;
  gap: 8px;
}

.icon-action {
  width: 32px;
  height: 32px;
  border: none;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.icon-action:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.icon-action.primary:hover {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}

.icon-action.success:hover {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.icon-action svg {
  width: 16px;
  height: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-state svg {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
}

.empty-state p {
  font-size: 13px;
  margin: 0;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.ticket-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
}
</style>
