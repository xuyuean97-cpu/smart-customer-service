<template>
  <div>
    <el-row :gutter="20" class="stat-row">
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ overview.total_conversations }}</div><div class="stat-label">总对话数</div></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ overview.active_users_today }}</div><div class="stat-label">活跃用户</div></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ overview.avg_quality_score }}</div><div class="stat-label">平均质量</div></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ overview.resolution_rate }}</div><div class="stat-label">解决率</div></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ overview.human_transfer_rate }}</div><div class="stat-label">转人工率</div></el-card></el-col>
      <el-col :span="4"><el-card shadow="hover"><div class="stat-val">{{ billing.total_requests }}</div><div class="stat-label">API 调用</div></el-card></el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px">
      <el-col :span="14">
        <el-card><div ref="trendChart" style="height:300px" /></el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="活跃用户排行">
          <el-table :data="topUsers" size="small" max-height="260">
            <el-table-column prop="user_id" label="用户" width="140" />
            <el-table-column prop="conversation_count" label="对话数" width="80" />
            <el-table-column prop="avg_quality" label="质量分" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import client from '../api/client'
import * as echarts from 'echarts'

const overview = ref({ total_conversations: 0, active_users_today: 0, avg_quality_score: 0, resolution_rate: 0, human_transfer_rate: 0 })
const topUsers = ref([])
const billing = ref({ total_requests: 0 })
const trendChart = ref(null)

onMounted(async () => {
  const [o, t, u, b] = await Promise.all([
    client.get('/api/v1/admin/dashboard/overview'),
    client.get('/api/v1/admin/dashboard/conversations/trend?days=7'),
    client.get('/api/v1/admin/dashboard/users/top?limit=10'),
    client.get('/api/v1/admin/billing/usage?days=30'),
  ])
  overview.value = o.data
  topUsers.value = u.data.users || []
  billing.value = b.data

  await nextTick()
  if (trendChart.value) {
    const chart = echarts.init(trendChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: (t.data.points || []).map(p => p.date.slice(5)) },
      yAxis: { type: 'value' },
      series: [{ name: '对话数', type: 'line', data: (t.data.points || []).map(p => p.count), smooth: true, areaStyle: {} }],
    })
  }
})
</script>

<style scoped>
.stat-val { font-size: 28px; font-weight: bold; color: #409eff; text-align: center; }
.stat-label { text-align: center; color: #909399; margin-top: 4px; }
.stat-row .el-card { text-align: center; }
</style>
