<template>
  <div class="settings-page">
    <!-- System Health Status -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon" :class="healthStatusClass">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>系统状态</h2>
          <p>监控各服务组件的健康状况</p>
        </div>
        <button class="refresh-btn" @click="loadHealthStatus" :disabled="healthLoading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: healthLoading }">
            <path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
          刷新
        </button>
      </div>
      <div class="settings-card health-card">
        <div class="health-overview">
          <div class="overall-status" :class="healthData.status">
            <span class="status-indicator"></span>
            <span class="status-text">{{ healthStatusText }}</span>
          </div>
          <div class="uptime-info" v-if="healthData.uptime_seconds">
            <span class="uptime-label">运行时间</span>
            <span class="uptime-value">{{ formatUptime(healthData.uptime_seconds) }}</span>
          </div>
        </div>
        <div class="health-grid">
          <!-- PostgreSQL -->
          <div class="health-item" :class="getServiceStatus(healthData.checks?.postgres)">
            <div class="health-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
              </svg>
            </div>
            <div class="health-content">
              <span class="health-name">PostgreSQL</span>
              <span class="health-status-text">{{ getServiceStatusText(healthData.checks?.postgres) }}</span>
            </div>
            <div class="health-badge" :class="getServiceStatus(healthData.checks?.postgres)">
              {{ getServiceStatus(healthData.checks?.postgres) }}
            </div>
            <div class="health-latency" v-if="healthData.checks?.postgres?.latency_ms">
              {{ healthData.checks.postgres.latency_ms }}ms
            </div>
          </div>

          <!-- ChromaDB -->
          <div class="health-item" :class="getServiceStatus(healthData.checks?.chromadb)">
            <div class="health-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
              </svg>
            </div>
            <div class="health-content">
              <span class="health-name">ChromaDB</span>
              <span class="health-status-text">{{ getServiceStatusText(healthData.checks?.chromadb) }}</span>
            </div>
            <div class="health-badge" :class="getServiceStatus(healthData.checks?.chromadb)">
              {{ getServiceStatus(healthData.checks?.chromadb) }}
            </div>
            <div class="circuit-status" v-if="healthData.checks?.chromadb?.circuit">
              <span v-if="healthData.checks.chromadb.circuit.circuit_open" class="circuit-open">
                熔断开启
              </span>
            </div>
          </div>

          <!-- LLM -->
          <div class="health-item" :class="getServiceStatus(healthData.checks?.llm)">
            <div class="health-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a2 2 0 110 4h-1.17A7.99 7.99 0 0112 22a8 8 0 01-8.83-4H2a2 2 0 110-4h1a7 7 0 017-7h1V5.73A2 2 0 0112 2z"/>
              </svg>
            </div>
            <div class="health-content">
              <span class="health-name">LLM 服务</span>
              <span class="health-status-text">
                {{ healthData.checks?.llm?.model || '未知模型' }}
              </span>
            </div>
            <div class="health-badge" :class="getServiceStatus(healthData.checks?.llm)">
              {{ getServiceStatus(healthData.checks?.llm) }}
            </div>
          </div>

          <!-- Redis -->
          <div class="health-item" :class="getServiceStatus(healthData.checks?.redis)">
            <div class="health-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
              </svg>
            </div>
            <div class="health-content">
              <span class="health-name">Redis</span>
              <span class="health-status-text">{{ getServiceStatusText(healthData.checks?.redis) }}</span>
            </div>
            <div class="health-badge" :class="getServiceStatus(healthData.checks?.redis)">
              {{ getServiceStatus(healthData.checks?.redis) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Account Security -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon purple">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0110 0v4"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>账户安全</h2>
          <p>管理您的登录凭证和安全设置</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="password-form">
          <div class="form-row">
            <div class="form-group">
              <label>当前手机号</label>
              <input type="text" :value="userPhone" disabled class="form-input disabled" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>当前密码</label>
              <input 
                v-model="passwordForm.oldPassword" 
                type="password" 
                placeholder="请输入当前密码"
                class="form-input"
              />
            </div>
          </div>
          <div class="form-row two-col">
            <div class="form-group">
              <label>新密码</label>
              <input 
                v-model="passwordForm.newPassword" 
                type="password" 
                placeholder="请输入新密码"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label>确认新密码</label>
              <input 
                v-model="passwordForm.confirmPassword" 
                type="password" 
                placeholder="请再次输入新密码"
                class="form-input"
              />
            </div>
          </div>
          <div class="password-requirements">
            <span class="req-title">密码要求:</span>
            <span class="req-item" :class="{ valid: passwordForm.newPassword.length >= 6 }">
              至少6位字符
            </span>
          </div>
          <div class="form-actions">
            <button class="primary-btn" @click="changePassword" :disabled="changingPassword">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
                <polyline points="17,21 17,13 7,13 7,21"/>
                <polyline points="7,3 7,8 15,8"/>
              </svg>
              {{ changingPassword ? '修改中...' : '修改密码' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Tenant Info -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>租户信息</h2>
          <p>管理您的租户配置和基本信息</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="info-grid">
          <div class="info-item">
            <label>租户ID</label>
            <div class="info-value">
              <span>default</span>
              <button class="copy-btn" @click="copyToClipboard('default')" title="复制">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="info-item">
            <label>名称</label>
            <div class="info-value">
              <span>默认租户</span>
            </div>
          </div>
          <div class="info-item">
            <label>API Key</label>
            <div class="info-value secret">
              <span>{{ showApiKey ? 'sk-demo-api-key-xxxxx' : '••••••••••••••••' }}</span>
              <button class="copy-btn" @click="showApiKey = !showApiKey" title="显示/隐藏">
                <svg v-if="!showApiKey" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>
                  <path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="info-item">
            <label>状态</label>
            <div class="info-value">
              <span class="status-badge active">
                <span class="status-dot"></span>
                启用
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- WeChat Config -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>微信配置</h2>
          <p>配置公众号接入参数</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="form-group">
          <label>公众号 Token</label>
          <div class="input-with-status">
            <input type="text" value="(未配置)" disabled class="form-input disabled" />
            <span class="config-status pending">待配置</span>
          </div>
        </div>
        <div class="form-group">
          <label>AppID</label>
          <div class="input-with-status">
            <input type="text" value="(未配置)" disabled class="form-input disabled" />
            <span class="config-status pending">待配置</span>
          </div>
        </div>
        <div class="form-group">
          <label>回调 URL</label>
          <div class="input-with-copy">
            <input type="text" :value="callbackUrl" disabled class="form-input" />
            <button class="copy-btn" @click="copyToClipboard(callbackUrl)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
              </svg>
            </button>
          </div>
          <span class="form-hint">将此 URL 填入微信公众平台服务器配置</span>
        </div>
        <div class="form-actions">
          <button class="primary-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
              <polyline points="17,21 17,13 7,13 7,21"/>
              <polyline points="7,3 7,8 15,8"/>
            </svg>
            保存配置
          </button>
        </div>
      </div>
    </div>

    <!-- Notification Settings -->
    <div class="settings-section">
      <div class="section-header">
        <div class="section-icon yellow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 01-3.46 0"/>
          </svg>
        </div>
        <div class="section-title">
          <h2>通知设置</h2>
          <p>配置系统通知和告警规则</p>
        </div>
      </div>
      <div class="settings-card">
        <div class="toggle-list">
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>新工单通知</h4>
              <p>当有新工单创建时发送通知</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="notifications.newTicket" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>异常告警</h4>
              <p>系统异常或服务中断时发送告警</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="notifications.systemAlert" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>每日报告</h4>
              <p>每日发送运营数据汇总报告</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="notifications.dailyReport" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="toggle-item">
            <div class="toggle-info">
              <h4>用量预警</h4>
              <p>当 API 用量接近限额时提醒</p>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="notifications.usageWarning" />
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { authApi, healthApi } from '../api'

const authStore = useAuthStore()

// Health check state
const healthData = ref({
  status: 'unknown',
  uptime_seconds: 0,
  checks: {}
})
const healthLoading = ref(false)

// Password change state
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const changingPassword = ref(false)

// Other state
const showApiKey = ref(false)
const notifications = reactive({
  newTicket: true,
  systemAlert: false,
  dailyReport: true,
  usageWarning: true
})

const userPhone = computed(() => authStore.user?.phone || '未知')
const callbackUrl = computed(() => {
  const host = window.location.origin
  return `${host}/api/v1/wechat/callback`
})

const healthStatusClass = computed(() => {
  const status = healthData.value.status
  if (status === 'ok') return 'green'
  if (status === 'degraded') return 'yellow'
  if (status === 'down') return 'red'
  return ''
})

const healthStatusText = computed(() => {
  const status = healthData.value.status
  if (status === 'ok') return '系统正常'
  if (status === 'degraded') return '部分降级'
  if (status === 'down') return '服务异常'
  return '检测中...'
})

function formatUptime(seconds) {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}天 ${hours}小时`
  if (hours > 0) return `${hours}小时 ${mins}分钟`
  return `${mins}分钟`
}

function getServiceStatus(service) {
  if (!service) return 'unknown'
  return service.status || 'unknown'
}

function getServiceStatusText(service) {
  if (!service) return '未知'
  const status = service.status
  if (status === 'ok') return '运行正常'
  if (status === 'degraded') return '性能降级'
  if (status === 'down') return '服务离线'
  return '未知状态'
}

async function loadHealthStatus() {
  healthLoading.value = true
  try {
    const resp = await healthApi.check()
    healthData.value = resp.data
  } catch (e) {
    healthData.value = {
      status: 'down',
      uptime_seconds: 0,
      checks: {}
    }
    ElMessage.error('健康检查失败')
  } finally {
    healthLoading.value = false
  }
}

async function changePassword() {
  if (!passwordForm.oldPassword) {
    ElMessage.warning('请输入当前密码')
    return
  }
  if (!passwordForm.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning('新密码至少需要6位字符')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  
  changingPassword.value = true
  try {
    await authApi.changePassword(
      authStore.user?.phone,
      passwordForm.oldPassword,
      passwordForm.newPassword
    )
    ElMessage.success('密码修改成功')
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (e) {
    ElMessage.error('密码修改失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    changingPassword.value = false
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

onMounted(() => {
  loadHealthStatus()
})
</script>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 800px;
}

.settings-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.section-icon {
  width: 44px;
  height: 44px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
  flex-shrink: 0;
}

.section-icon svg { width: 22px; height: 22px; }
.section-icon.green { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); }
.section-icon.yellow { background: rgba(234, 179, 8, 0.15); color: var(--accent-yellow); }
.section-icon.purple { background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); }
.section-icon.blue { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
.section-icon.red { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }

.section-title {
  flex: 1;
}

.section-title h2 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.section-title p {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.refresh-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-btn svg {
  width: 14px;
  height: 14px;
}

.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.settings-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  transition: all 0.2s ease;
}

.settings-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
}

/* Health Card */
.health-card {
  padding: 20px;
}

.health-overview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.overall-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-muted);
}

.overall-status.ok .status-indicator {
  background: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green);
  animation: pulse 2s infinite;
}

.overall-status.degraded .status-indicator {
  background: var(--accent-yellow);
  box-shadow: 0 0 8px var(--accent-yellow);
}

.overall-status.down .status-indicator {
  background: var(--accent-red);
  box-shadow: 0 0 8px var(--accent-red);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.uptime-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.uptime-label {
  font-size: 11px;
  color: var(--text-muted);
}

.uptime-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.health-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.health-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--text-muted);
}

.health-item.ok {
  border-left-color: var(--accent-green);
}

.health-item.degraded {
  border-left-color: var(--accent-yellow);
}

.health-item.down {
  border-left-color: var(--accent-red);
}

.health-icon {
  width: 36px;
  height: 36px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.health-icon svg {
  width: 18px;
  height: 18px;
}

.health-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.health-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.health-status-text {
  font-size: 11px;
  color: var(--text-muted);
}

.health-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.health-badge.ok {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.health-badge.degraded {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.health-badge.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.health-badge.unknown {
  background: rgba(161, 161, 170, 0.15);
  color: var(--text-muted);
}

.health-latency {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
}

.circuit-status .circuit-open {
  font-size: 10px;
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

/* Password Form */
.password-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.form-group:last-of-type {
  margin-bottom: 0;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input {
  width: 100%;
  height: 42px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 14px;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
}

.form-input:focus {
  border-color: var(--accent-blue);
}

.form-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.password-requirements {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.req-title {
  color: var(--text-secondary);
}

.req-item {
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.req-item.valid {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 14px;
  color: var(--text-primary);
}

.info-value.secret span {
  letter-spacing: 2px;
}

.copy-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: auto;
  transition: all 0.15s ease;
}

.copy-btn:hover {
  background: var(--bg-elevated);
  color: var(--accent-blue);
}

.copy-btn svg { width: 16px; height: 16px; }

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.status-badge.active {
  color: var(--accent-green);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--accent-green);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.input-with-status {
  position: relative;
  display: flex;
  align-items: center;
}

.input-with-status .form-input {
  padding-right: 100px;
}

.config-status {
  position: absolute;
  right: 12px;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.config-status.pending {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.config-status.configured {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.input-with-copy {
  display: flex;
  gap: 8px;
}

.input-with-copy .form-input { flex: 1; }

.input-with-copy .copy-btn {
  width: 42px;
  height: 42px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.form-hint {
  display: block;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 8px;
}

.form-actions {
  padding-top: 8px;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  height: 42px;
  background: var(--accent-blue);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
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

.primary-btn svg { width: 18px; height: 18px; }

/* Toggle List */
.toggle-list {
  display: flex;
  flex-direction: column;
}

.toggle-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.15s ease;
}

.toggle-item:hover .toggle-info h4 {
  color: var(--accent-blue);
}

.toggle-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.toggle-item:first-child {
  padding-top: 0;
}

.toggle-info h4 {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  transition: color 0.15s ease;
}

.toggle-info p {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.toggle-switch {
  position: relative;
  width: 44px;
  height: 24px;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  inset: 0;
  background: var(--bg-tertiary);
  border-radius: 24px;
  transition: all 0.2s ease;
}

.slider::before {
  content: '';
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: var(--text-muted);
  border-radius: 50%;
  transition: all 0.2s ease;
}

.toggle-switch input:checked + .slider {
  background: var(--accent-blue);
}

.toggle-switch input:checked + .slider::before {
  background: white;
  transform: translateX(20px);
}
</style>
