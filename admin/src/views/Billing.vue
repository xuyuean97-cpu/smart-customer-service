<template>
  <div>
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6"><el-card shadow="hover"><div class="stat-val">{{ formatNum(data.total_tokens_in) }}</div><div class="stat-label">输入 Token</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><div class="stat-val">{{ formatNum(data.total_tokens_out) }}</div><div class="stat-label">输出 Token</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><div class="stat-val">{{ formatNum(data.total_tokens_in + data.total_tokens_out) }}</div><div class="stat-label">总 Token</div></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><div class="stat-val">{{ data.total_requests }}</div><div class="stat-label">总请求数</div></el-card></el-col>
    </el-row>
    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="12"><el-card header="按模型分布"><div ref="pieChart" style="height:280px" /></el-card></el-col>
      <el-col :span="12"><el-card header="按日期"><div ref="barChart" style="height:280px" /></el-card></el-col>
    </el-row>
    <el-card style="margin-top:20px" header="调用明细">
      <el-table :data="detailData" max-height="400" size="small">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="tokens" label="Token" width="100" />
        <el-table-column prop="requests" label="请求数" width="80" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import client from '../api/client'
import * as echarts from 'echarts'

const data = reactive({ total_tokens_in: 0, total_tokens_out: 0, total_requests: 0, by_model: {}, by_date: [] })
const pieChart = ref(null)
const barChart = ref(null)
const detailData = ref([])

function formatNum(n) { return n > 1000 ? (n/1000).toFixed(1)+'k' : n }

onMounted(async () => {
  const resp = await client.get('/api/v1/admin/billing/usage?days=30')
  Object.assign(data, resp.data)
  detailData.value = resp.data.by_date || []

  await nextTick()
  if (pieChart.value) {
    const pie = echarts.init(pieChart.value)
    const models = Object.entries(data.by_model || {})
    pie.setOption({
      tooltip: { trigger: 'item' },
      series: [{ type: 'pie', radius: ['40%','70%'], data: models.map(([k,v]) => ({ name: k, value: v })) }],
    })
  }
  if (barChart.value) {
    const bar = echarts.init(barChart.value)
    const dates = (data.by_date || []).slice(-14)
    bar.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: dates.map(d => d.date.slice(5)) },
      yAxis: { type: 'value' },
      series: [{ name: 'Token', type: 'bar', data: dates.map(d => d.tokens) }],
    })
  }
})
</script>

<style scoped>
.stat-val { font-size: 28px; font-weight: bold; color: #409eff; text-align: center; }
.stat-label { text-align: center; color: #909399; margin-top: 4px; }
</style>
