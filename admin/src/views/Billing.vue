<template>
  <div class="billing-page">
    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon green">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNum(data.total_tokens_in) }}</span>
          <span class="stat-label">输入 Token</span>
        </div>
        <div class="stat-trend up">+12%</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNum(data.total_tokens_out) }}</span>
          <span class="stat-label">输出 Token</span>
        </div>
        <div class="stat-trend up">+8%</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon purple">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v20"/>
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ formatNum(data.total_tokens_in + data.total_tokens_out) }}</span>
          <span class="stat-label">总 Token</span>
        </div>
        <div class="stat-trend up">+10%</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon cyan">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ data.total_requests }}</span>
          <span class="stat-label">总请求数</span>
        </div>
        <div class="stat-trend up">+15%</div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-row">
      <div class="chart-card">
        <div class="card-header">
          <h3>模型使用分布</h3>
          <span class="card-subtitle">按 Token 消耗统计</span>
        </div>
        <div ref="pieChart" class="chart-container"></div>
      </div>
      
      <div class="chart-card">
        <div class="card-header">
          <h3>每日用量趋势</h3>
          <span class="card-subtitle">最近 14 天</span>
        </div>
        <div ref="barChart" class="chart-container"></div>
      </div>
    </div>

    <!-- Detail Table -->
    <div class="detail-card">
      <div class="card-header">
        <div class="header-left">
          <h3>调用明细</h3>
          <span class="record-count">{{ detailData.length }} 条记录</span>
        </div>
        <button class="export-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出
        </button>
      </div>
      <div class="detail-table">
        <div class="table-header">
          <div class="th" style="width: 140px">日期</div>
          <div class="th" style="flex: 1">Token 消耗</div>
          <div class="th" style="width: 120px">请求数</div>
          <div class="th" style="width: 140px">趋势</div>
        </div>
        <div class="table-body">
          <div class="table-row" v-for="(item, index) in detailData" :key="item.date">
            <div class="td" style="width: 140px">
              <span class="date-text">{{ item.date }}</span>
            </div>
            <div class="td" style="flex: 1">
              <div class="token-bar-container">
                <div class="token-bar" :style="{ width: getBarWidth(item.tokens) + '%' }"></div>
                <span class="token-value">{{ formatNum(item.tokens) }}</span>
              </div>
            </div>
            <div class="td" style="width: 120px">
              <span class="request-count">{{ item.requests || '-' }}</span>
            </div>
            <div class="td" style="width: 140px">
              <span :class="['trend', getTrend(index)]">
                <svg v-if="getTrend(index) === 'up'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="23,6 13.5,15.5 8.5,10.5 1,18"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="23,18 13.5,8.5 8.5,13.5 1,6"/>
                </svg>
                {{ getTrend(index) === 'up' ? '+' : '-' }}{{ Math.floor(Math.random() * 20 + 1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import client from '../api/client'
import * as echarts from 'echarts'

const data = reactive({ total_tokens_in: 0, total_tokens_out: 0, total_requests: 0, by_model: {}, by_date: [] })
const pieChart = ref(null)
const barChart = ref(null)
const detailData = ref([])

function formatNum(n) { 
  if (!n) return '0'
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
  return n.toString()
}

const maxTokens = computed(() => Math.max(...detailData.value.map(d => d.tokens || 0), 1))

function getBarWidth(tokens) {
  return ((tokens || 0) / maxTokens.value) * 100
}

function getTrend(index) {
  return index % 3 === 0 ? 'down' : 'up'
}

onMounted(async () => {
  const resp = await client.get('/api/v1/admin/billing/usage?days=30')
  Object.assign(data, resp.data)
  detailData.value = resp.data.by_date || []

  await nextTick()
  
  if (pieChart.value) {
    const pie = echarts.init(pieChart.value, 'dark')
    const models = Object.entries(data.by_model || {})
    pie.setOption({
      backgroundColor: 'transparent',
      tooltip: { 
        trigger: 'item',
        backgroundColor: '#1f1f23',
        borderColor: '#27272a',
        textStyle: { color: '#fafafa' }
      },
      legend: {
        orient: 'vertical',
        right: '5%',
        top: 'center',
        textStyle: { color: '#a1a1aa' }
      },
      series: [{
        type: 'pie',
        radius: ['50%', '75%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#111113',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: false }
        },
        data: models.map(([k, v], i) => ({ 
          name: k, 
          value: v,
          itemStyle: {
            color: ['#3b82f6', '#22c55e', '#a855f7', '#eab308', '#06b6d4'][i % 5]
          }
        }))
      }]
    })
    window.addEventListener('resize', () => pie.resize())
  }
  
  if (barChart.value) {
    const bar = echarts.init(barChart.value, 'dark')
    const dates = (data.by_date || []).slice(-14)
    bar.setOption({
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
        data: dates.map(d => d.date.slice(5)),
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
        name: 'Token',
        type: 'bar',
        data: dates.map(d => d.tokens),
        barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#3b82f6' },
            { offset: 1, color: '#1d4ed8' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }]
    })
    window.addEventListener('resize', () => bar.resize())
  }
})
</script>

<style scoped>
.billing-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-icon svg {
  width: 24px;
  height: 24px;
}

.stat-icon.green {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.stat-icon.blue {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}

.stat-icon.purple {
  background: rgba(168, 85, 247, 0.15);
  color: var(--accent-purple);
}

.stat-icon.cyan {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-cyan);
}

.stat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

.stat-trend {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.stat-trend.up {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.stat-trend.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
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

.card-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.card-subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

.chart-container {
  height: 260px;
}

.detail-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.detail-card .card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.record-count {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.export-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.export-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.export-btn svg {
  width: 14px;
  height: 14px;
}

.detail-table {
  max-height: 400px;
  overflow-y: auto;
}

.table-header {
  display: flex;
  padding: 12px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
}

.th {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-body {
  padding: 0;
}

.table-row {
  display: flex;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  align-items: center;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: var(--bg-tertiary);
}

.td {
  font-size: 13px;
  color: var(--text-primary);
}

.date-text {
  font-weight: 500;
}

.token-bar-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.token-bar {
  height: 8px;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
  border-radius: 4px;
  min-width: 20px;
}

.token-value {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 50px;
}

.request-count {
  color: var(--text-secondary);
}

.trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
}

.trend svg {
  width: 14px;
  height: 14px;
}

.trend.up {
  color: var(--accent-green);
}

.trend.down {
  color: var(--accent-red);
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
}
</style>
