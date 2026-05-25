<template>
  <div class="expert-review-page">
    <!-- Search Filters -->
    <div class="search-section">
      <div class="search-title">🔍 查询条件</div>
      <div class="search-grid">
        <div class="form-group">
          <label>用户ID</label>
          <input v-model="filters.user_id" placeholder="输入用户ID筛选" class="form-input" />
        </div>
        <div class="form-group">
          <label>智能体ID</label>
          <input v-model="filters.agent_id" placeholder="输入智能体ID" class="form-input" />
        </div>
        <div class="form-group">
          <label>会话ID</label>
          <input v-model="filters.run_id" placeholder="输入会话ID" class="form-input" />
        </div>
        <div class="form-group">
          <label>审核状态</label>
          <select v-model="filters.expert_verified" class="form-input">
            <option value="">全部状态</option>
            <option value="false">待审核</option>
            <option value="true">已审核</option>
          </select>
        </div>
        <div class="form-group">
          <label>开始日期</label>
          <input v-model="filters.start_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label>结束日期</label>
          <input v-model="filters.end_date" type="date" class="form-input" />
        </div>
        <div class="form-group">
          <label>返回数量</label>
          <input v-model.number="filters.limit" type="number" class="form-input" min="1" max="1000" />
        </div>
      </div>
      <div class="search-actions">
        <button class="btn btn-secondary" @click="clearFilters">🗑️ 清空条件</button>
        <button class="btn btn-primary" @click="loadConversations" :disabled="loading">
          {{ loading ? '查询中...' : '🔍 开始查询' }}
        </button>
      </div>
    </div>

    <!-- Results -->
    <div class="results-section" v-if="searched">
      <div class="results-header">
        <div>
          <div class="results-title">📋 审核结果</div>
          <div class="results-count">共 {{ conversations.length }} 条记录</div>
        </div>
        <div class="batch-actions" v-if="conversations.length">
          <div class="selected-info" v-if="selectedIds.size">已选 {{ selectedIds.size }} 条</div>
          <div class="batch-controls">
            <label>批量评分:</label>
            <input v-model.number="batchScore" type="number" class="score-input" min="0" max="1" step="0.1" />
            <button class="btn btn-sm btn-success" @click="batchApprove">✅ 批量通过</button>
            <button class="btn btn-sm btn-danger" @click="batchReject">❌ 批量拒绝</button>
          </div>
        </div>
      </div>

      <div class="table-wrap" v-if="conversations.length">
        <table class="results-table">
          <thead>
            <tr>
              <th width="3%">选择</th>
              <th width="13%">基本信息</th>
              <th width="42%">对话内容</th>
              <th width="8%">状态</th>
              <th width="34%">审核操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="conv in pagedConversations" :key="conv.memory_id"
                :class="{ selected: selectedIds.has(conv.memory_id), 'conv-row': true }">
              <td>
                <input type="checkbox" :checked="selectedIds.has(conv.memory_id)"
                       @change="toggleSelect(conv.memory_id)" :disabled="conv.expert_verified" />
              </td>
              <td>
                <div class="conv-meta">
                  <div><strong>用户:</strong> {{ conv.user_id }}</div>
                  <div><strong>会话:</strong> {{ (conv.run_id || '').slice(0, 12) }}...</div>
                  <div><strong>智能体:</strong> {{ conv.agent_id }}</div>
                  <div><strong>时间:</strong> {{ fmt(conv.created_at) }}</div>
                </div>
              </td>
              <td>
                <div class="conv-content">
                  <div class="query-text">
                    <strong>🙋 用户:</strong> {{ conv.query || '无内容' }}
                  </div>
                  <div class="response-text">
                    <strong>🤖 AI:</strong> {{ conv.response || '无回复' }}
                  </div>
                  <div class="retrieval-info" v-if="conv.retrieval_source || conv.retrieval_content">
                    <strong>📚 检索来源:</strong> {{ conv.retrieval_source || '-' }}
                    <span class="score-badge" v-if="conv.retrieval_score">匹配: {{ conv.retrieval_score?.toFixed(3) }}</span>
                  </div>
                </div>
              </td>
              <td>
                <span class="status-badge" :class="conv.expert_verified ? 'approved' : 'pending'">
                  {{ conv.expert_verified ? '✅ 已审核' : '⏳ 待审核' }}
                </span>
                <div v-if="conv.expert_verified" style="font-size:11px;color:var(--text-muted);margin-top:4px">
                  评分: {{ conv.quality_score }}
                </div>
              </td>
              <td>
                <div v-if="conv.expert_verified" style="font-size:12px;color:var(--text-muted)">
                  审核于 {{ fmt(conv.updated_at) }}
                </div>
                <div v-else class="review-controls">
                  <div class="control-row">
                    <label>质量评分:</label>
                    <input v-model.number="reviewScores[conv.memory_id]" type="number"
                           class="score-input" min="0" max="1" step="0.1" />
                  </div>
                  <textarea v-model="reviewCorrections[conv.memory_id]" class="correction-input"
                            placeholder="修正回复（可选）" rows="3" />
                  <input v-model="reviewNotes[conv.memory_id]" class="notes-input" placeholder="审核备注（可选）" />
                  <div class="action-row">
                    <button class="btn btn-sm btn-success" @click="approveOne(conv)">✅ 通过</button>
                    <button class="btn btn-sm btn-danger" @click="rejectOne(conv)">❌ 拒绝</button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="empty-state" v-else>
        <h3>🔍 没有找到符合条件的记录</h3>
        <p>尝试调整查询条件或扩大时间范围</p>
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="totalPages > 1">
        <button class="page-btn" :disabled="page <= 1" @click="page--">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="page++">下一页</button>
      </div>
    </div>

    <div class="empty-state" v-if="!searched" style="margin-top:40px">
      <h3>🔍 专家审核工作台</h3>
      <p>设置查询条件后点击"开始查询"加载待审核对话</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

const loading = ref(false)
const searched = ref(false)
const conversations = ref([])
const selectedIds = ref(new Set())
const page = ref(1)
const pageSize = 20
const batchScore = ref(0.9)

const filters = reactive({
  user_id: '', agent_id: '', run_id: '', application_id: '电商主智能客服',
  expert_verified: '', start_date: '', end_date: '', limit: 50,
})

// Per-row review state
const reviewScores = reactive({})
const reviewCorrections = reactive({})
const reviewNotes = reactive({})

const totalPages = computed(() => Math.ceil(conversations.value.length / pageSize))
const pagedConversations = computed(() => {
  const start = (page.value - 1) * pageSize
  return conversations.value.slice(start, start + pageSize)
})

function fmt(ts) {
  if (!ts) return '-'
  return ts.slice(0, 19).replace('T', ' ')
}

function clearFilters() {
  filters.user_id = ''; filters.agent_id = ''; filters.run_id = ''
  filters.expert_verified = ''; filters.start_date = ''; filters.end_date = ''
  filters.limit = 50
}

async function loadConversations() {
  loading.value = true; searched.value = true
  try {
    const params = {}
    for (const [k, v] of Object.entries(filters)) {
      if (v !== '' && v !== null) params[k] = v
    }
    const resp = await client.get('/memory/v1/conversations/history', { params })
    conversations.value = resp.data.conversations || []

    // Init review state
    for (const c of conversations.value) {
      if (!reviewScores[c.memory_id]) reviewScores[c.memory_id] = 0.8
      if (!reviewCorrections[c.memory_id]) reviewCorrections[c.memory_id] = ''
      if (!reviewNotes[c.memory_id]) reviewNotes[c.memory_id] = ''
    }
    selectedIds.value.clear()
    page.value = 1
  } catch {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function toggleSelect(id) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
  selectedIds.value = new Set(selectedIds.value)
}

async function approveOne(conv) {
  const score = reviewScores[conv.memory_id] ?? 0.8
  try {
    await client.post('/memory/v1/conversations/expert-review', {
      memory_id: conv.memory_id,
      query: conv.query || '',
      response: conv.response || '',
      expert_approved: true,
      quality_score: score,
      corrected_response: reviewCorrections[conv.memory_id] || null,
      review_notes: reviewNotes[conv.memory_id] || null,
    })
    ElMessage.success('✅ 审核通过')
    conv.expert_verified = true
    conv.quality_score = score
  } catch {
    ElMessage.error('操作失败')
  }
}

async function rejectOne(conv) {
  try {
    await client.post('/memory/v1/conversations/expert-review', {
      memory_id: conv.memory_id,
      query: conv.query || '',
      response: conv.response || '',
      expert_approved: false,
      quality_score: 0,
      corrected_response: null,
      review_notes: reviewNotes[conv.memory_id] || '审核拒绝',
    })
    ElMessage.success('❌ 已拒绝')
    conv.expert_verified = true
    conv.quality_score = 0
  } catch {
    ElMessage.error('操作失败')
  }
}

async function batchApprove() {
  if (!selectedIds.value.size) return ElMessage.warning('请先选择记录')
  const ids = [...selectedIds.value]
  await ElMessageBox.confirm(`确定批量通过 ${ids.length} 条记录？`)
  try {
    const items = ids.map(id => {
      const c = conversations.value.find(c => c.memory_id === id)
      return {
        memory_id: id,
        query: c?.query || '',
        response: c?.response || '',
        expert_approved: true,
        quality_score: batchScore.value,
        review_notes: '批量审核通过',
      }
    })
    await client.post('/memory/v1/conversations/batch-expert-review', { review_items: items })
    ElMessage.success(`✅ 批量通过 ${ids.length} 条`)
    selectedIds.value.clear()
    loadConversations()
  } catch { ElMessage.error('批量操作失败') }
}

async function batchReject() {
  if (!selectedIds.value.size) return ElMessage.warning('请先选择记录')
  const ids = [...selectedIds.value]
  await ElMessageBox.confirm(`确定批量拒绝 ${ids.length} 条记录？`)
  try {
    const items = ids.map(id => {
      const c = conversations.value.find(c => c.memory_id === id)
      return {
        memory_id: id,
        query: c?.query || '',
        response: c?.response || '',
        expert_approved: false,
        quality_score: 0,
        review_notes: '批量审核拒绝',
      }
    })
    await client.post('/memory/v1/conversations/batch-expert-review', { review_items: items })
    ElMessage.success(`❌ 批量拒绝 ${ids.length} 条`)
    selectedIds.value.clear()
    loadConversations()
  } catch { ElMessage.error('批量操作失败') }
}
</script>

<style scoped>
.expert-review-page { display: flex; flex-direction: column; gap: 20px; }
.search-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px; }
.search-title { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; }
.search-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-group label { font-size: 12px; font-weight: 500; color: var(--text-muted); text-transform: uppercase; letter-spacing: .5px; }
.form-input { height: 38px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; padding: 0 12px; font-size: 13px; color: var(--text-primary); outline: none; }
.form-input:focus { border-color: var(--accent-blue); }
.search-actions { display: flex; gap: 12px; justify-content: flex-end; }

.btn { padding: 10px 20px; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all .15s; }
.btn:disabled { opacity: .6; cursor: not-allowed; }
.btn-primary { background: var(--accent-blue); color: #fff; }
.btn-primary:hover { filter: brightness(1.1); }
.btn-secondary { background: var(--bg-tertiary); color: var(--text-secondary); border: 1px solid var(--border-color); }
.btn-sm { padding: 6px 12px; font-size: 12px; border-radius: 6px; }
.btn-success { background: var(--accent-green); color: #fff; }
.btn-danger { background: var(--accent-red); color: #fff; }

.results-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); overflow: hidden; }
.results-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-color); flex-wrap: wrap; gap: 12px; }
.results-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.results-count { font-size: 12px; color: var(--text-muted); }
.batch-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.selected-info { background: var(--accent-blue); color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.batch-controls { display: flex; align-items: center; gap: 8px; }
.batch-controls label { font-size: 12px; color: var(--text-muted); white-space: nowrap; }

.table-wrap { overflow-x: auto; }
.results-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.results-table th { background: var(--bg-tertiary); padding: 12px; text-align: left; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border-color); font-size: 11px; white-space: nowrap; }
.results-table td { padding: 12px; border-bottom: 1px solid var(--border-color); vertical-align: top; }
.conv-row:hover { background: var(--bg-tertiary); }
.conv-row.selected { background: rgba(59,130,246,.08); border-left: 3px solid var(--accent-blue); }

.conv-meta { display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: var(--text-secondary); }
.conv-meta strong { color: var(--text-primary); }
.conv-content { display: flex; flex-direction: column; gap: 8px; }
.query-text { background: rgba(59,130,246,.06); padding: 10px; border-radius: 8px; border-left: 3px solid var(--accent-blue); font-size: 13px; line-height: 1.5; }
.response-text { background: rgba(34,197,94,.06); padding: 10px; border-radius: 8px; border-left: 3px solid var(--accent-green); font-size: 13px; line-height: 1.5; }
.retrieval-info { font-size: 12px; background: rgba(139,92,246,.06); padding: 8px 10px; border-radius: 6px; border-left: 3px solid #8b5cf6; }

.status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.status-badge.pending { background: rgba(234,179,8,.15); color: var(--accent-yellow); }
.status-badge.approved { background: rgba(34,197,94,.15); color: var(--accent-green); }
.score-badge { font-size: 11px; background: var(--accent-blue); color: #fff; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }

.review-controls { display: flex; flex-direction: column; gap: 8px; }
.control-row { display: flex; align-items: center; gap: 8px; }
.control-row label { font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.score-input { width: 60px; padding: 4px 8px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 4px; text-align: center; font-size: 13px; color: var(--text-primary); }
.correction-input, .notes-input { width: 100%; padding: 8px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 12px; color: var(--text-primary); resize: vertical; font-family: inherit; }
.correction-input:focus, .notes-input:focus, .score-input:focus { border-color: var(--accent-blue); outline: none; }
.action-row { display: flex; gap: 6px; margin-top: 4px; }

.pagination { display: flex; justify-content: center; align-items: center; gap: 12px; padding: 16px; border-top: 1px solid var(--border-color); }
.page-btn { padding: 8px 16px; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; font-size: 13px; color: var(--text-secondary); cursor: pointer; }
.page-btn:hover:not(:disabled) { border-color: var(--accent-blue); color: var(--accent-blue); }
.page-btn:disabled { opacity: .4; cursor: not-allowed; }

.empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
.empty-state h3 { font-size: 18px; color: var(--text-secondary); margin-bottom: 8px; }
</style>
