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
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="搜索工单..." 
            class="search-input" 
          />
        </div>
        <div class="ws-status" :class="wsConnected ? 'connected' : 'disconnected'">
          <span class="ws-dot"></span>
          {{ wsConnected ? '实时连接' : '未连接' }}
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
        <div class="th" style="width: 100px">用户ID</div>
        <div class="th" style="width: 80px">优先级</div>
        <div class="th" style="width: 90px">状态</div>
        <div class="th" style="width: 100px">坐席</div>
        <div class="th" style="width: 160px">创建时间</div>
        <div class="th" style="width: 140px">操作</div>
      </div>
      <div class="table-body">
        <div 
          class="table-row" 
          v-for="ticket in filteredTickets" 
          :key="ticket.id"
          :class="{ highlight: highlightedId === ticket.id }"
        >
          <div class="td" style="width: 100px">
            <span class="ticket-id">#{{ ticket.id?.slice(-8) }}</span>
          </div>
          <div class="td" style="flex: 1">
            <span class="ticket-summary">{{ ticket.summary }}</span>
          </div>
          <div class="td" style="width: 100px">
            <span class="user-id-text">{{ ticket.user_id || '-' }}</span>
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
            <span class="time-text">{{ formatTime(ticket.created_at) }}</span>
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
        <div v-if="!loading && filteredTickets.length === 0" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
          </svg>
          <h3>{{ searchQuery ? '未找到匹配工单' : '暂无工单' }}</h3>
          <p>{{ searchQuery ? '尝试其他搜索关键词' : '当前筛选条件下没有工单数据' }}</p>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
      </div>
    </div>

    <!-- Ticket Detail Drawer -->
    <el-drawer 
      v-model="drawerVisible" 
      :title="currentTicket ? `工单 #${currentTicket.id?.slice(-8)}` : '工单详情'"
      size="520px"
      class="ticket-drawer"
    >
      <div v-if="currentTicket" class="drawer-content">
        <!-- Status Banner -->
        <div class="status-banner" :class="currentTicket.status">
          <span :class="['status-badge', currentTicket.status]">
            {{ statusMap[currentTicket.status] }}
          </span>
          <span :class="['priority-badge', currentTicket.priority]">
            {{ priorityMap[currentTicket.priority] }} 优先级
          </span>
        </div>

        <!-- Basic Info -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">工单ID</span>
              <span class="info-value mono">{{ currentTicket.id }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">用户ID</span>
              <span class="info-value">{{ currentTicket.user_id || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">处理坐席</span>
              <span class="info-value">{{ currentTicket.agent_id || '未分配' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ formatTime(currentTicket.created_at) }}</span>
            </div>
          </div>
        </div>

        <!-- Summary -->
        <div class="detail-section">
          <h4>工单摘要</h4>
          <div class="summary-box">
            {{ currentTicket.summary }}
          </div>
        </div>

        <!-- Resolution Note -->
        <div class="detail-section" v-if="currentTicket.resolution_note">
          <h4>处理备注</h4>
          <div class="note-box">
            {{ currentTicket.resolution_note }}
          </div>
        </div>

        <!-- Timeline (Mock) -->
        <div class="detail-section">
          <h4>工单动态</h4>
          <div class="timeline">
            <div class="timeline-item">
              <div class="timeline-dot created"></div>
              <div class="timeline-content">
                <span class="timeline-title">工单创建</span>
                <span class="timeline-time">{{ formatTime(currentTicket.created_at) }}</span>
              </div>
            </div>
            <div class="timeline-item" v-if="currentTicket.agent_id">
              <div class="timeline-dot assigned"></div>
              <div class="timeline-content">
                <span class="timeline-title">{{ currentTicket.agent_id }} 接手处理</span>
                <span class="timeline-time">{{ formatTime(currentTicket.updated_at) }}</span>
              </div>
            </div>
            <div class="timeline-item" v-if="currentTicket.status === 'resolved'">
              <div class="timeline-dot resolved"></div>
              <div class="timeline-content">
                <span class="timeline-title">工单已解决</span>
                <span class="timeline-time">{{ formatTime(currentTicket.updated_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="drawer-actions">
          <button 
            v-if="currentTicket.status === 'open'" 
            class="action-btn primary"
            @click="assignTicket(currentTicket); drawerVisible = false"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <line x1="20" y1="8" x2="20" y2="14"/>
              <line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
            接手处理
          </button>
          <button 
            v-if="currentTicket.status === 'in_progress'" 
            class="action-btn success"
            @click="resolveTicket(currentTicket)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
            标记解决
          </button>
          <button 
            v-if="currentTicket.user_id"
            class="action-btn"
            @click="viewUserConversations"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            查看对话
          </button>
        </div>
      </div>
    </el-drawer>

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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { ticketsApi } from '../api'

const router = useRouter()

const tickets = ref([])
const loading = ref(false)
const filterStatus = ref('')
const searchQuery = ref('')
const dialogVisible = ref(false)
const creating = ref(false)
const newTicket = ref({ user_id: '', priority: 'medium', summary: '' })

// Drawer state
const drawerVisible = ref(false)
const currentTicket = ref(null)

// WebSocket state
const wsConnected = ref(false)
let wsConnection = null

// Highlight newly created ticket
const highlightedId = ref(null)

const statusOptions = ref([
  { value: '', label: '全部', count: null },
  { value: 'open', label: '待处理', count: 0 },
  { value: 'in_progress', label: '处理中', count: 0 },
  { value: 'resolved', label: '已解决', count: null }
])

const priorityMap = { medium: '中', high: '高', urgent: '紧急' }
const statusMap = { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }

const filteredTickets = computed(() => {
  if (!searchQuery.value.trim()) return tickets.value
  const q = searchQuery.value.toLowerCase()
  return tickets.value.filter(t => 
    t.summary?.toLowerCase().includes(q) ||
    t.id?.toLowerCase().includes(q) ||
    t.user_id?.toLowerCase().includes(q)
  )
})

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return timeStr.slice(0, 16).replace('T', ' ')
}

function updateStatusCounts() {
  const openCount = tickets.value.filter(t => t.status === 'open').length
  const progressCount = tickets.value.filter(t => t.status === 'in_progress').length
  statusOptions.value[1].count = openCount || null
  statusOptions.value[2].count = progressCount || null
}

async function loadTickets() {
  loading.value = true
  try {
    const params = { tenant_id: 'default', limit: 100 }
    if (filterStatus.value) params.status = filterStatus.value
    const resp = await ticketsApi.list(params)
    tickets.value = resp.data.tickets || []
    updateStatusCounts()
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function createTicket() {
  if (!newTicket.value.summary.trim()) {
    ElMessage.warning('请填写工单摘要')
    return
  }
  creating.value = true
  try {
    await ticketsApi.create(newTicket.value)
    ElMessage.success('工单已创建')
    dialogVisible.value = false
    newTicket.value = { user_id: '', priority: 'medium', summary: '' }
    loadTickets()
  } catch (e) {
    ElMessage.error('创建失败')
  } finally { 
    creating.value = false 
  }
}

async function assignTicket(row) {
  try {
    await ticketsApi.update(row.id, { status: 'in_progress', agent_id: 'admin' })
    ElMessage.success('已接手')
    loadTickets()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function resolveTicket(row) {
  try {
    const { value } = await ElMessageBox.prompt('处理备注', '解决工单', {
      confirmButtonText: '确认解决',
      cancelButtonText: '取消',
      inputPlaceholder: '请输入处理备注（可选）'
    })
    await ticketsApi.update(row.id, { status: 'resolved', resolution_note: value || '' })
    ElMessage.success('已解决')
    drawerVisible.value = false
    loadTickets()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

function openDetail(ticket) {
  currentTicket.value = ticket
  drawerVisible.value = true
}

function viewUserConversations() {
  if (currentTicket.value?.user_id) {
    drawerVisible.value = false
    router.push({ path: '/conversations', query: { user_id: currentTicket.value.user_id } })
  }
}

// WebSocket connection
function connectWebSocket() {
  const { close } = ticketsApi.connectWebSocket(
    // onMessage
    (data) => {
      if (data.type === 'new_ticket') {
        ElNotification({
          title: '新工单通知',
          message: `收到新工单: ${data.summary || '待处理'}`,
          type: 'warning',
          duration: 5000,
          position: 'top-right',
        })
        // Highlight the new ticket
        highlightedId.value = data.ticket_id
        setTimeout(() => {
          highlightedId.value = null
        }, 3000)
        loadTickets()
      } else if (data.type === 'ticket_updated') {
        loadTickets()
      }
    },
    // onError
    () => {
      wsConnected.value = false
    },
    // onClose
    () => {
      wsConnected.value = false
    }
  )
  
  wsConnected.value = true
  wsConnection = { close }
}

onMounted(() => {
  loadTickets()
  connectWebSocket()
})

onUnmounted(() => {
  wsConnection?.close()
})
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

.filter-tab:hover { color: var(--text-primary); }

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

.ws-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
}

.ws-status.connected {
  background: rgba(34, 197, 94, 0.1);
  color: var(--accent-green);
}

.ws-status.disconnected {
  background: rgba(161, 161, 170, 0.1);
  color: var(--text-muted);
}

.ws-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.ws-status.connected .ws-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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

.primary-btn:hover { background: var(--accent-blue-hover); }
.primary-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.primary-btn svg { width: 16px; height: 16px; }

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
  transition: all 0.2s ease;
}

.table-row:hover {
  background: var(--bg-tertiary);
}

.table-row:hover .ticket-id {
  color: var(--accent-blue);
  background: rgba(59, 130, 246, 0.15);
}

.table-row.highlight {
  background: rgba(234, 179, 8, 0.1);
  animation: highlightFade 3s ease-out;
}

@keyframes highlightFade {
  0% { background: rgba(234, 179, 8, 0.2); }
  100% { background: transparent; }
}

.table-row:last-child { border-bottom: none; }

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
  transition: all 0.2s ease;
}

.ticket-summary {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.user-id-text {
  font-size: 12px;
  color: var(--text-secondary);
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

.agent-name { color: var(--text-secondary); }

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

.icon-action svg { width: 16px; height: 16px; }

/* Empty & Loading States */
.empty-state, .loading-state {
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

.loading-state { gap: 12px; }

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Drawer Styles */
.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: var(--radius-md);
}

.status-banner.open {
  background: rgba(239, 68, 68, 0.1);
}

.status-banner.in_progress {
  background: rgba(234, 179, 8, 0.1);
}

.status-banner.resolved {
  background: rgba(34, 197, 94, 0.1);
}

.detail-section h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
}

.info-value {
  font-size: 13px;
  color: var(--text-primary);
}

.info-value.mono {
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
}

.summary-box, .note-box {
  padding: 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.note-box {
  background: rgba(34, 197, 94, 0.1);
  border-left: 3px solid var(--accent-green);
}

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 12px;
  padding: 12px 0;
  position: relative;
}

.timeline-item:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 32px;
  bottom: -12px;
  width: 2px;
  background: var(--border-color);
}

.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
}

.timeline-dot.created { background: var(--accent-blue); }
.timeline-dot.assigned { background: var(--accent-yellow); }
.timeline-dot.resolved { background: var(--accent-green); }

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.timeline-title {
  font-size: 13px;
  color: var(--text-primary);
}

.timeline-time {
  font-size: 11px;
  color: var(--text-muted);
}

.drawer-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.drawer-actions .action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--border-color);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.drawer-actions .action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.drawer-actions .action-btn.primary {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
  color: white;
}

.drawer-actions .action-btn.primary:hover {
  background: var(--accent-blue-hover);
}

.drawer-actions .action-btn.success {
  background: var(--accent-green);
  border-color: var(--accent-green);
  color: white;
}

.drawer-actions .action-btn.success:hover {
  filter: brightness(1.1);
}

.drawer-actions .action-btn svg {
  width: 16px;
  height: 16px;
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
