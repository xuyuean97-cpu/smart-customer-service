<template>
  <div class="dashboard">
    <!-- Top Toolbar -->
    <div class="dashboard-toolbar">
      <div class="toolbar-left">
        <h2>运营概览</h2>
      </div>
      <div class="toolbar-right">
        <div class="filter-group">
          <label>租户</label>
          <select v-model="tenantId" class="filter-select" @change="loadDashboard">
            <option value="default">默认租户</option>
            <option value="tenant_001">租户 001</option>
            <option value="tenant_002">租户 002</option>
          </select>
        </div>
        <div class="filter-group">
          <label>时间范围</label>
          <div class="btn-group">
            <button 
              v-for="opt in dateOptions" 
              :key="opt.value"
              :class="['btn-option', { active: selectedDays === opt.value }]"
              @click="selectDays(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
        <button class="download-btn" @click="downloadReport" :disabled="downloadingReport">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ downloadingReport ? '下载中...' : '下载报告' }}
        </button>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
          </div>
          <div class="stat-trend up" v-if="overview.total_conversations > 0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
            </svg>
            <span>+12%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(overview.total_conversations) }}</div>
        <div class="stat-label">总对话数</div>
        <div class="stat-chart">
          <div class="mini-bar" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/>
              <path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
          </div>
          <div class="stat-trend up">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
            </svg>
            <span>+8%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(overview.active_users_today) }}</div>
        <div class="stat-label">活跃用户</div>
        <div class="stat-chart">
          <div class="mini-bar green" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
            </svg>
          </div>
          <div class="stat-trend up">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
            </svg>
            <span>+5%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatPercent(overview.avg_quality_score) }}</div>
        <div class="stat-label">平均质量分</div>
        <div class="stat-chart">
          <div class="mini-bar purple" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon cyan">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          </div>
          <div class="stat-trend up">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
            </svg>
            <span>+3%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatPercent(overview.resolution_rate) }}</div>
        <div class="stat-label">解决率</div>
        <div class="stat-chart">
          <div class="mini-bar cyan" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon yellow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <line x1="20" y1="8" x2="20" y2="14"/>
              <line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
          </div>
          <div class="stat-trend down">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,18 13.5,8.5 8.5,13.5 1,6"/>
            </svg>
            <span>-2%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatPercent(overview.human_transfer_rate) }}</div>
        <div class="stat-label">转人工率</div>
        <div class="stat-chart">
          <div class="mini-bar yellow" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon red">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <div class="stat-trend up">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
            </svg>
            <span>+18%</span>
          </div>
        </div>
        <div class="stat-value">{{ formatNumber(billing.total_requests) }}</div>
        <div class="stat-label">API 调用</div>
        <div class="stat-chart">
          <div class="mini-bar red" v-for="i in 7" :key="i" :style="{ height: Math.random() * 100 + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- Performance Cards (New) -->
    <div class="performance-section" v-if="performance">
      <h3 class="section-title">性能指标</h3>
      <div class="performance-grid">
        <div class="perf-card">
          <div class="perf-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          </div>
          <div class="perf-content">
            <span class="perf-value">{{ formatPercent(performance.resolution_rate) }}</span>
            <span class="perf-label">问题解决率</span>
          </div>
          <div class="perf-bar">
            <div class="perf-fill green" :style="{ width: (performance.resolution_rate || 0) * 100 + '%' }"></div>
          </div>
        </div>
        <div class="perf-card">
          <div class="perf-icon yellow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="8.5" cy="7" r="4"/>
              <line x1="20" y1="8" x2="20" y2="14"/>
              <line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
          </div>
          <div class="perf-content">
            <span class="perf-value">{{ formatPercent(performance.human_transfer_rate) }}</span>
            <span class="perf-label">转人工比例</span>
          </div>
          <div class="perf-bar">
            <div class="perf-fill yellow" :style="{ width: (performance.human_transfer_rate || 0) * 100 + '%' }"></div>
          </div>
        </div>
        <div class="perf-card">
          <div class="perf-icon purple">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
            </svg>
          </div>
          <div class="perf-content">
            <span class="perf-value">{{ formatPercent(performance.avg_quality_score) }}</span>
            <span class="perf-label">平均服务质量</span>
          </div>
          <div class="perf-bar">
            <div class="perf-fill purple" :style="{ width: (performance.avg_quality_score || 0) * 100 + '%' }"></div>
          </div>
        </div>
        <div class="perf-card">
          <div class="perf-icon blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="4" y1="21" x2="4" y2="14"/>
              <line x1="4" y1="10" x2="4" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12" y2="3"/>
              <line x1="20" y1="21" x2="20" y2="16"/>
              <line x1="20" y1="12" x2="20" y2="3"/>
            </svg>
          </div>
          <div class="perf-content">
            <span class="perf-value">{{ performance.avg_response_length || 0 }}</span>
            <span class="perf-label">平均回复长度</span>
          </div>
          <div class="perf-bar">
            <div class="perf-fill blue" style="width: 65%"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="charts-section">
      <div class="chart-card large">
        <div class="card-header">
          <div class="card-title">
            <h3>对话趋势</h3>
            <span class="card-subtitle">最近 {{ selectedDays }} 天</span>
          </div>
          <div class="card-actions">
            <button 
              v-for="opt in dateOptions" 
              :key="opt.value"
              :class="['action-btn', { active: selectedDays === opt.value }]"
              @click="selectDays(opt.value)"
            >
              {{ opt.shortLabel }}
            </button>
          </div>
        </div>
        <div ref="trendChart" class="chart-container"></div>
      </div>
      
      <div class="chart-card">
        <div class="card-header">
          <div class="card-title">
            <h3>活跃用户排行</h3>
            <span class="card-subtitle">Top 10</span>
          </div>
          <button class="view-all-btn" @click="$router.push('/users')">查看全部</button>
        </div>
        <div class="user-list">
          <div class="user-item" v-for="(user, index) in topUsers" :key="user.user_id">
            <div class="user-rank" :class="{ top3: index < 3 }">{{ index + 1 }}</div>
            <div class="user-avatar-small">{{ user.user_id?.charAt(0)?.toUpperCase() || 'U' }}</div>
            <div class="user-details">
              <div class="user-id">{{ user.user_id || '未知用户' }}</div>
              <div class="user-meta">{{ user.conversation_count }} 对话</div>
            </div>
            <div class="user-score">
              <span class="score-value">{{ user.avg_quality ? (user.avg_quality * 100).toFixed(0) + '%' : '-' }}</span>
              <span class="score-label">质量分</span>
            </div>
          </div>
          <div v-if="!topUsers.length" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>暂无数据</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <div class="action-card" @click="$router.push('/tickets')">
        <div class="action-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
          </svg>
        </div>
        <div class="action-content">
          <h4>待处理工单</h4>
          <p>查看需要处理的工单</p>
        </div>
        <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9,18 15,12 9,6"/>
        </svg>
      </div>
      
      <div class="action-card" @click="$router.push('/conversations')">
        <div class="action-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <div class="action-content">
          <h4>查看对话</h4>
          <p>浏览历史对话记录</p>
        </div>
        <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9,18 15,12 9,6"/>
        </svg>
      </div>
      
      <div class="action-card" @click="$router.push('/billing')">
        <div class="action-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
            <line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
        </div>
        <div class="action-content">
          <h4>用量详情</h4>
          <p>查看 API 使用情况</p>
        </div>
        <svg class="action-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9,18 15,12 9,6"/>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { dashboardApi, billingApi } from '../api'
import * as echarts from 'echarts'

const tenantId = ref('default')
const selectedDays = ref(7)
const downloadingReport = ref(false)

const dateOptions = [
  { value: 7, label: '7天', shortLabel: '日' },
  { value: 14, label: '14天', shortLabel: '周' },
  { value: 30, label: '30天', shortLabel: '月' },
]

const overview = ref({ 
  total_conversations: 0, 
  active_users_today: 0, 
  avg_quality_score: 0, 
  resolution_rate: 0, 
  human_transfer_rate: 0 
})
const performance = ref(null)
const topUsers = ref([])
const billing = ref({ total_requests: 0 })
const trendChart = ref(null)
let chartInstance = null

function formatNumber(n) {
  if (!n) return '0'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

function formatPercent(n) {
  if (!n && n !== 0) return '-'
  if (n <= 1) return (n * 100).toFixed(0) + '%'
  return n.toFixed(0) + '%'
}

function selectDays(days) {
  selectedDays.value = days
  loadTrend()
}

async function loadDashboard() {
  const [o, p, u, b] = await Promise.all([
    dashboardApi.getOverview(tenantId.value),
    dashboardApi.getPerformance(tenantId.value),
    dashboardApi.getTopUsers(tenantId.value, 10),
    billingApi.getUsage(tenantId.value, 30),
  ])
  overview.value = o.data
  performance.value = p.data
  topUsers.value = u.data.users || []
  billing.value = b.data
  
  await loadTrend()
}

async function loadTrend() {
  const t = await dashboardApi.getConversationTrend(tenantId.value, selectedDays.value)
  await nextTick()
  
  if (trendChart.value) {
    if (!chartInstance) {
      chartInstance = echarts.init(trendChart.value, 'dark')
      window.addEventListener('resize', () => chartInstance?.resize())
    }
    
    const points = t.data.points || []
    chartInstance.setOption({
      backgroundColor: 'transparent',
      tooltip: { 
        trigger: 'axis',
        backgroundColor: '#1f1f23',
        borderColor: '#27272a',
        textStyle: { color: '#fafafa' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true
      },
      xAxis: { 
        type: 'category', 
        data: points.map(p => p.date.slice(5)),
        axisLine: { lineStyle: { color: '#27272a' } },
        axisLabel: { color: '#71717a' },
        axisTick: { show: false }
      },
      yAxis: { 
        type: 'value',
        axisLine: { show: false },
        axisLabel: { color: '#71717a' },
        splitLine: { lineStyle: { color: '#27272a', type: 'dashed' } }
      },
      series: [{
        name: '对话数',
        type: 'line',
        data: points.map(p => p.count),
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#3b82f6',
          width: 3
        },
        itemStyle: {
          color: '#3b82f6',
          borderWidth: 2,
          borderColor: '#fff'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ])
        }
      }]
    })
  }
}

async function downloadReport() {
  downloadingReport.value = true
  try {
    const resp = await dashboardApi.getOperationalReport(tenantId.value)
    const report = resp.data
    
    // Generate report content
    const content = `运营报告 - ${new Date().toLocaleDateString()}
=======================================
租户ID: ${tenantId.value}
生成时间: ${new Date().toLocaleString()}

概览指标:
- 总对话数: ${overview.value.total_conversations}
- 活跃用户: ${overview.value.active_users_today}
- 平均质量分: ${formatPercent(overview.value.avg_quality_score)}
- 解决率: ${formatPercent(overview.value.resolution_rate)}
- 转人工率: ${formatPercent(overview.value.human_transfer_rate)}

API 用量:
- 总请求数: ${billing.value.total_requests}
- 输入 Token: ${billing.value.total_tokens_in}
- 输出 Token: ${billing.value.total_tokens_out}

${JSON.stringify(report, null, 2)}
`
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `operational_report_${new Date().toISOString().slice(0,10)}.txt`
    link.click()
    URL.revokeObjectURL(link.href)
    
    ElMessage.success('报告已下载')
  } catch (e) {
    ElMessage.error('下载失败: ' + (e.message || '未知错误'))
  } finally {
    downloadingReport.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Toolbar */
.dashboard-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.dashboard-toolbar h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.filter-select {
  height: 34px;
  padding: 0 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: var(--accent-blue);
}

.btn-group {
  display: flex;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 3px;
}

.btn-option {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.btn-option:hover {
  color: var(--text-primary);
}

.btn-option.active {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 34px;
  background: var(--accent-blue);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.download-btn:hover {
  background: var(--accent-blue-hover);
}

.download-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.download-btn svg {
  width: 16px;
  height: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all 0.2s ease;
  animation: cardFadeIn 0.4s ease-out backwards;
}

.stat-card:nth-child(1) { animation-delay: 0.05s; }
.stat-card:nth-child(2) { animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation-delay: 0.15s; }
.stat-card:nth-child(4) { animation-delay: 0.2s; }
.stat-card:nth-child(5) { animation-delay: 0.25s; }
.stat-card:nth-child(6) { animation-delay: 0.3s; }

.stat-card:hover {
  border-color: var(--accent-blue);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 20px;
  height: 20px;
}

.stat-icon.blue { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }
.stat-icon.green { background: rgba(34, 197, 94, 0.15); color: var(--accent-green); }
.stat-icon.purple { background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); }
.stat-icon.cyan { background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan); }
.stat-icon.yellow { background: rgba(234, 179, 8, 0.15); color: var(--accent-yellow); }
.stat-icon.red { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
}

.stat-trend svg { width: 14px; height: 14px; }
.stat-trend.up { color: var(--accent-green); }
.stat-trend.down { color: var(--accent-red); }

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.stat-chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 32px;
  margin-top: auto;
}

.mini-bar {
  flex: 1;
  background: var(--accent-blue);
  border-radius: 2px;
  opacity: 0.6;
  min-height: 4px;
}

.mini-bar.green { background: var(--accent-green); }
.mini-bar.purple { background: var(--accent-purple); }
.mini-bar.cyan { background: var(--accent-cyan); }
.mini-bar.yellow { background: var(--accent-yellow); }
.mini-bar.red { background: var(--accent-red); }

/* Performance Section */
.performance-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.perf-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.perf-icon {
  width: 40px;
  height: 40px;
  background: rgba(34, 197, 94, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-green);
}

.perf-icon.yellow { background: rgba(234, 179, 8, 0.15); color: var(--accent-yellow); }
.perf-icon.purple { background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); }
.perf-icon.blue { background: rgba(59, 130, 246, 0.15); color: var(--accent-blue); }

.perf-icon svg {
  width: 20px;
  height: 20px;
}

.perf-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.perf-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.perf-label {
  font-size: 13px;
  color: var(--text-muted);
}

.perf-bar {
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.perf-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.perf-fill.green { background: var(--accent-green); }
.perf-fill.yellow { background: var(--accent-yellow); }
.perf-fill.purple { background: var(--accent-purple); }
.perf-fill.blue { background: var(--accent-blue); }

.charts-section {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.card-title h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.card-subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  gap: 4px;
  background: var(--bg-tertiary);
  padding: 4px;
  border-radius: var(--radius-md);
}

.action-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.action-btn:hover { color: var(--text-secondary); }
.action-btn.active { background: var(--bg-elevated); color: var(--text-primary); }

.view-all-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.15s ease;
}

.view-all-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.chart-container { height: 300px; }

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  transition: all 0.15s ease;
}

.user-item:hover { background: var(--bg-elevated); }

.user-rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border-radius: 50%;
}

.user-rank.top3 {
  background: linear-gradient(135deg, var(--accent-yellow), #f59e0b);
  color: #000;
}

.user-avatar-small {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-cyan) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
}

.user-details { flex: 1; min-width: 0; }

.user-id {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-meta { font-size: 11px; color: var(--text-muted); }

.user-score { text-align: right; }

.score-value {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-green);
}

.score-label { font-size: 10px; color: var(--text-muted); }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--text-muted);
  gap: 8px;
}

.empty-state svg { width: 32px; height: 32px; opacity: 0.5; }

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-card:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent-blue);
  transform: translateX(4px);
}

.action-card:hover .action-arrow {
  transform: translateX(4px);
  color: var(--accent-blue);
}

.action-icon {
  width: 48px;
  height: 48px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
}

.action-icon svg { width: 24px; height: 24px; }

.action-content { flex: 1; }

.action-content h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.action-content p {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.action-arrow {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  transition: all 0.2s ease;
}

@media (max-width: 1400px) {
  .stats-grid { grid-template-columns: repeat(3, 1fr); }
  .performance-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 1200px) {
  .charts-section { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .quick-actions { grid-template-columns: 1fr; }
  .toolbar-right { flex-wrap: wrap; }
}
</style>
