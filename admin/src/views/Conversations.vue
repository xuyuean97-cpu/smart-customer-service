<template>
  <div class="conversations-page">
    <!-- Filter Card -->
    <div class="filter-card">
      <div class="filter-row">
        <div class="filter-item">
          <label>用户ID</label>
          <input 
            v-model="filters.user_id" 
            type="text" 
            placeholder="输入用户ID筛选"
            class="filter-input"
          />
        </div>
        <div class="filter-item">
          <label>智能体</label>
          <select v-model="filters.agent_id" class="filter-input">
            <option value="">全部智能体</option>
            <option value="电商主智能客服">电商主智能客服</option>
            <option value="售后客服">售后客服</option>
            <option value="咨询助手">咨询助手</option>
          </select>
        </div>
        <div class="filter-item">
          <label>开始日期</label>
          <input 
            v-model="filters.start_date" 
            type="date" 
            class="filter-input"
          />
        </div>
        <div class="filter-item">
          <label>结束日期</label>
          <input 
            v-model="filters.end_date" 
            type="date" 
            class="filter-input"
          />
        </div>
      </div>
      <div class="filter-row">
        <div class="filter-item search-item">
          <label>关键词搜索</label>
          <div class="search-input-wrapper">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="搜索对话内容..."
              class="filter-input with-icon"
              @keyup.enter="handleSearch"
            />
          </div>
        </div>
        <div class="filter-item">
          <label>智能过滤</label>
          <select v-model="smartFilterType" class="filter-input">
            <option value="">不过滤</option>
            <option value="low_quality">低质量回复</option>
            <option value="negative">负面情绪</option>
            <option value="unresolved">未解决问题</option>
          </select>
        </div>
        <div class="filter-actions">
          <button class="search-btn" @click="loadHistory">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            查询
          </button>
          <button class="reset-btn" @click="resetFilters">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
            </svg>
            重置
          </button>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="record-count">共 {{ conversations.length }} 条记录</span>
        <span v-if="selectedIds.size > 0" class="selected-count">
          已选 {{ selectedIds.size }} 条
        </span>
      </div>
      <div class="toolbar-right">
        <button 
          v-if="selectedIds.size > 0" 
          class="toolbar-btn" 
          @click="batchReview"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 11l3 3L22 4"/>
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
          批量审核
        </button>
        <button class="toolbar-btn" @click="exportCsv">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导出 CSV
        </button>
      </div>
    </div>

    <!-- Conversations List -->
    <div class="conversations-list">
      <div class="list-header">
        <label class="checkbox-wrapper">
          <input 
            type="checkbox" 
            :checked="isAllSelected" 
            @change="toggleSelectAll"
          />
          <span class="checkmark"></span>
        </label>
        <h3>对话记录</h3>
      </div>
      
      <div class="conversation-items">
        <div 
          v-for="(conv, index) in conversations" 
          :key="conv.memory_id || index" 
          class="conversation-item"
          :class="{ selected: selectedIds.has(conv.memory_id) }"
        >
          <label class="checkbox-wrapper item-checkbox">
            <input 
              type="checkbox" 
              :checked="selectedIds.has(conv.memory_id)"
              @change="toggleSelect(conv.memory_id)"
            />
            <span class="checkmark"></span>
          </label>
          
          <div class="conv-main">
            <div class="conv-header">
              <div class="conv-meta">
                <div class="user-info">
                  <div class="user-avatar">
                    {{ (conv.user_id || 'U').charAt(0).toUpperCase() }}
                  </div>
                  <div class="user-details">
                    <span class="user-id">{{ conv.user_id || '未知用户' }}</span>
                    <span class="conv-time">{{ formatTime(conv.created_at) }}</span>
                  </div>
                </div>
                <div class="conv-badges">
                  <span v-if="conv.agent_id" class="agent-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/>
                      <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                      <line x1="9" y1="9" x2="9.01" y2="9"/>
                      <line x1="15" y1="9" x2="15.01" y2="9"/>
                    </svg>
                    {{ conv.agent_id }}
                  </span>
                  <span v-if="conv.quality_score" class="quality-badge" :class="getQualityClass(conv.quality_score)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
                    </svg>
                    {{ (conv.quality_score * 100).toFixed(0) }}%
                  </span>
                  <span v-if="conv.user_approved === 1" class="approved-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3z"/>
                      <path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/>
                    </svg>
                  </span>
                  <span v-if="conv.user_approved === 0 && conv.user_approved !== undefined" class="disapproved-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M10 15V19a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3z"/>
                      <path d="M17 2h3a2 2 0 012 2v7a2 2 0 01-2 2h-3"/>
                    </svg>
                  </span>
                </div>
              </div>
            </div>
            
            <div class="conv-content">
              <div class="message question">
                <div class="message-label">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/>
                    <line x1="12" y1="17" x2="12.01" y2="17"/>
                  </svg>
                  问题
                </div>
                <div class="message-text">{{ conv.query || '无内容' }}</div>
              </div>
              <div class="message answer">
                <div class="message-label">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                  </svg>
                  回复
                </div>
                <div class="message-text">{{ conv.response || '无回复' }}</div>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="conv-actions">
              <button 
                class="action-btn feedback-btn like" 
                :class="{ active: conv.user_approved === 1 }"
                @click="submitFeedback(conv, 1)"
                title="点赞"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3z"/>
                  <path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/>
                </svg>
              </button>
              <button 
                class="action-btn feedback-btn dislike"
                :class="{ active: conv.user_approved === 0 }"
                @click="submitFeedback(conv, 0)"
                title="点踩"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10 15V19a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3z"/>
                  <path d="M17 2h3a2 2 0 012 2v7a2 2 0 01-2 2h-3"/>
                </svg>
              </button>
              <button 
                class="action-btn review-btn"
                @click="openReviewDialog(conv)"
                title="专家审核"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <!-- Empty State -->
        <div v-if="!loading && !conversations.length" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <h3>暂无对话记录</h3>
          <p>尝试调整筛选条件或稍后再试</p>
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
      </div>
    </div>

    <!-- Expert Review Dialog -->
    <el-dialog v-model="reviewDialogVisible" title="专家审核" width="640px" class="review-dialog" @closed="resetReviewForm">
      <div class="review-content" v-if="currentReviewConv">
        <!-- 上下文信息 -->
        <div class="review-header">
          <div class="review-meta">
            <span class="meta-tag">用户: {{ currentReviewConv.user_id }}</span>
            <span class="meta-tag">来源: {{ currentReviewConv.query_source || '未知' }}</span>
            <span class="meta-tag">设备: {{ currentReviewConv.query_device || '未知' }}</span>
            <span class="meta-tag">时间: {{ formatTime(currentReviewConv.created_at) }}</span>
          </div>
        </div>

        <!-- 对话内容 -->
        <div class="review-preview">
          <div class="preview-label">🙋 用户问题</div>
          <div class="preview-text user-query">{{ currentReviewConv.query || '无内容' }}</div>
          <div class="preview-label">🤖 AI 回复</div>
          <div class="preview-text ai-response">{{ currentReviewConv.response || '无回复' }}</div>
        </div>

        <!-- 审核决策 -->
        <div class="review-decision">
          <div class="decision-row">
            <span class="decision-label">审核结论</span>
            <el-radio-group v-model="reviewApproved">
              <el-radio :value="true">✅ 通过</el-radio>
              <el-radio :value="false">❌ 驳回</el-radio>
            </el-radio-group>
          </div>

          <div class="form-item">
            <label>质量评分 (0-100)</label>
            <el-slider v-model="reviewScore" :min="0" :max="100" :step="5" show-input />
            <div class="score-hint" :class="scoreLevel">{{ scoreHint }}</div>
          </div>

          <!-- 驳回时显示修正回复 -->
          <div class="form-item" v-if="!reviewApproved">
            <label>修正回复 (建议的正确回复)</label>
            <el-input v-model="correctedResponse" type="textarea" :rows="4" placeholder="请输入修正后的正确回复..." />
          </div>

          <div class="form-item">
            <label>审核备注</label>
            <el-input v-model="reviewFeedback" type="textarea" :rows="2" placeholder="请输入审核意见..." />
          </div>
        </div>
      </div>
      <template #footer>
        <button class="secondary-btn" @click="reviewDialogVisible = false">取消</button>
        <button class="danger-btn" v-if="!reviewApproved" @click="submitReview" :disabled="submittingReview">
          {{ submittingReview ? '提交中...' : '确认驳回' }}
        </button>
        <button class="primary-btn" @click="submitReview" :disabled="submittingReview || !reviewApproved">
          {{ submittingReview ? '提交中...' : reviewApproved ? '确认通过' : '请选择结论' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { conversationsApi } from '../api'

const route = useRoute()

const conversations = ref([])
const loading = ref(false)
const searchQuery = ref('')
const smartFilterType = ref('')

const filters = reactive({ 
  user_id: '', 
  agent_id: '',
  start_date: '',
  end_date: '',
})

// 从路由参数初始化筛选条件
onMounted(() => {
  if (route.query.user_id) {
    filters.user_id = route.query.user_id
  }
})

// 多选状态
const selectedIds = ref(new Set())

const isAllSelected = computed(() => {
  if (conversations.value.length === 0) return false
  return conversations.value.every(c => selectedIds.value.has(c.memory_id))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value.clear()
  } else {
    conversations.value.forEach(c => {
      if (c.memory_id) selectedIds.value.add(c.memory_id)
    })
  }
  selectedIds.value = new Set(selectedIds.value)
}

function toggleSelect(id) {
  if (!id) return
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  selectedIds.value = new Set(selectedIds.value)
}

// 专家审核相关
const reviewDialogVisible = ref(false)
const currentReviewConv = ref(null)
const submittingReview = ref(false)
const reviewApproved = ref(true)
const reviewScore = ref(80)
const reviewFeedback = ref('')
const correctedResponse = ref('')

const scoreHint = computed(() => {
  if (reviewScore.value >= 80) return '优秀，可以直接作为专家示例录入知识库'
  if (reviewScore.value >= 60) return '良好，建议优化后可录入知识库'
  return '需要改进，建议驳回并修正回复'
})
const scoreLevel = computed(() => {
  if (reviewScore.value >= 80) return 'good'
  if (reviewScore.value >= 60) return 'warn'
  return 'bad'
})

function resetReviewForm() {
  reviewApproved.value = true
  reviewScore.value = 80
  reviewFeedback.value = ''
  correctedResponse.value = ''
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return timeStr.slice(0, 19).replace('T', ' ')
}

function getQualityClass(score) {
  if (score >= 0.8) return 'high'
  if (score >= 0.5) return 'medium'
  return 'low'
}

function resetFilters() {
  filters.user_id = ''
  filters.agent_id = ''
  filters.start_date = ''
  filters.end_date = ''
  searchQuery.value = ''
  smartFilterType.value = ''
  loadHistory()
}

async function loadHistory() {
  loading.value = true
  selectedIds.value.clear()
  try {
    const params = {}
    if (filters.user_id) params.user_id = filters.user_id
    if (filters.agent_id) params.agent_id = filters.agent_id
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    
    const resp = await conversationsApi.getHistory(params)
    conversations.value = resp.data.conversations || []
  } catch (e) {
    conversations.value = []
    ElMessage.error('加载失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) {
    loadHistory()
    return
  }
  loading.value = true
  try {
    const resp = await conversationsApi.search(searchQuery.value)
    conversations.value = resp.data.conversations || resp.data || []
  } catch (e) {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

async function submitFeedback(conv, approved) {
  try {
    await conversationsApi.userFeedback(conv.response, approved)
    conv.user_approved = approved
    ElMessage.success(approved === 1 ? '已点赞' : '已点踩')
  } catch (e) {
    ElMessage.error('反馈提交失败')
  }
}

function openReviewDialog(conv) {
  currentReviewConv.value = conv
  reviewScore.value = conv.quality_score ? Math.round(conv.quality_score * 100) : 80
  reviewFeedback.value = ''
  reviewDialogVisible.value = true
}

async function submitReview() {
  if (!currentReviewConv.value) return
  submittingReview.value = true
  try {
    await conversationsApi.expertReview({
      memory_id: currentReviewConv.value.memory_id,
      query: currentReviewConv.value.query || '',
      response: currentReviewConv.value.response || '',
      expert_approved: reviewScore.value >= 60,
      quality_score: reviewScore.value / 100,
      corrected_response: correctedResponse.value || null,
      review_notes: reviewFeedback.value || '',
    })
    currentReviewConv.value.quality_score = reviewScore.value / 100
    ElMessage.success('审核已提交')
    reviewDialogVisible.value = false
  } catch (e) {
    ElMessage.error('提交失败')
  } finally {
    submittingReview.value = false
  }
}

async function batchReview() {
  const ids = Array.from(selectedIds.value)
  if (ids.length === 0) return

  try {
    const items = ids.map(id => {
      const conv = conversations.value.find(c => c.memory_id === id)
      return {
        memory_id: id,
        query: conv?.query || '',
        expert_approved: true,
        quality_score: 0.8,
        review_notes: '批量审核通过',
      }
    })
    await conversationsApi.batchExpertReview(items)
    ElMessage.success(`已批量审核 ${ids.length} 条记录`)
    selectedIds.value.clear()
    loadHistory()
  } catch (e) {
    ElMessage.error('批量审核失败')
  }
}

function exportCsv() {
  if (conversations.value.length === 0) {
    ElMessage.warning('暂无数据可导出')
    return
  }
  const filename = `conversations_${new Date().toISOString().slice(0,10)}.csv`
  conversationsApi.exportToCsv(conversations.value, filename)
  ElMessage.success('导出成功')
}

// 初始加载
loadHistory()
</script>

<style scoped>
.conversations-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-item.search-item {
  flex: 1;
  min-width: 200px;
}

.filter-item label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-input {
  min-width: 160px;
  height: 38px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.filter-input:focus {
  border-color: var(--accent-blue);
}

.search-input-wrapper {
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

.filter-input.with-icon {
  padding-left: 38px;
  width: 100%;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.search-btn, .reset-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 38px;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.search-btn {
  background: var(--accent-blue);
  color: white;
}

.search-btn:hover {
  background: var(--accent-blue-hover);
}

.reset-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.reset-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.search-btn svg, .reset-btn svg {
  width: 16px;
  height: 16px;
}

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.record-count {
  font-size: 13px;
  color: var(--text-muted);
}

.selected-count {
  font-size: 13px;
  color: var(--accent-blue);
  font-weight: 500;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.toolbar-btn {
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

.toolbar-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
  border-color: var(--accent-blue);
}

.toolbar-btn svg {
  width: 14px;
  height: 14px;
}

/* Conversations List */
.conversations-list {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.list-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* Checkbox */
.checkbox-wrapper {
  position: relative;
  display: inline-flex;
  cursor: pointer;
}

.checkbox-wrapper input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
  height: 0;
  width: 0;
}

.checkmark {
  width: 18px;
  height: 18px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  transition: all 0.15s ease;
}

.checkbox-wrapper:hover .checkmark {
  border-color: var(--accent-blue);
}

.checkbox-wrapper input:checked ~ .checkmark {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
}

.checkbox-wrapper input:checked ~ .checkmark::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.conversation-items {
  max-height: calc(100vh - 420px);
  overflow-y: auto;
}

.conversation-item {
  display: flex;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.conversation-item:hover {
  background: var(--bg-tertiary);
}

.conversation-item.selected {
  background: rgba(59, 130, 246, 0.08);
}

.conversation-item:last-child {
  border-bottom: none;
}

.item-checkbox {
  padding-top: 4px;
}

.conv-main {
  flex: 1;
  min-width: 0;
}

.conv-header {
  margin-bottom: 16px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-cyan) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.conversation-item:hover .user-avatar {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-id {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.conv-time {
  font-size: 12px;
  color: var(--text-muted);
}

.conv-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-badge, .quality-badge, .approved-badge, .disapproved-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}

.agent-badge {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}

.agent-badge svg {
  width: 12px;
  height: 12px;
}

.quality-badge {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.quality-badge.high {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.quality-badge.low {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
}

.quality-badge svg {
  width: 12px;
  height: 12px;
}

.approved-badge {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
  padding: 4px 8px;
}

.approved-badge svg {
  width: 14px;
  height: 14px;
}

.disapproved-badge {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-red);
  padding: 4px 8px;
}

.disapproved-badge svg {
  width: 14px;
  height: 14px;
}

.conv-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.message {
  padding: 14px 16px;
  border-radius: var(--radius-md);
}

.message.question {
  background: var(--bg-tertiary);
}

.message.answer {
  background: rgba(59, 130, 246, 0.1);
  border-left: 3px solid var(--accent-blue);
}

.message-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.message-label svg {
  width: 14px;
  height: 14px;
}

.message-text {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
}

/* Action Buttons */
.conv-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

.feedback-btn.like:hover, .feedback-btn.like.active {
  background: rgba(34, 197, 94, 0.15);
  border-color: var(--accent-green);
  color: var(--accent-green);
}

.feedback-btn.dislike:hover, .feedback-btn.dislike.active {
  background: rgba(239, 68, 68, 0.15);
  border-color: var(--accent-red);
  color: var(--accent-red);
}

.review-btn:hover {
  background: rgba(59, 130, 246, 0.15);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

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

.loading-state {
  gap: 12px;
}

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

/* Review Dialog */
.review-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.review-preview {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 16px;
}

.preview-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.preview-label:not(:first-child) {
  margin-top: 12px;
}

.preview-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}

.review-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.primary-btn, .secondary-btn {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.primary-btn {
  background: var(--accent-blue);
  border: none;
  color: white;
}

.primary-btn:hover {
  background: var(--accent-blue-hover);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  margin-right: 12px;
}

.secondary-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.review-header { margin-bottom: 4px; }
.review-meta { display: flex; flex-wrap: wrap; gap: 8px; }
.meta-tag { font-size: 11px; padding: 2px 10px; background: var(--bg-tertiary); border-radius: 12px; color: var(--text-muted); }
.user-query { border-left: 3px solid var(--accent-blue); padding-left: 12px; }
.ai-response { border-left: 3px solid var(--accent-green); padding-left: 12px; }
.review-decision { display: flex; flex-direction: column; gap: 16px; }
.decision-row { display: flex; align-items: center; gap: 16px; }
.decision-label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.score-hint { font-size: 12px; margin-top: 4px; padding: 4px 8px; border-radius: 4px; }
.score-hint.good { background: rgba(34,197,94,0.1); color: var(--accent-green); }
.score-hint.warn { background: rgba(234,179,8,0.1); color: var(--accent-yellow); }
.score-hint.bad { background: rgba(239,68,68,0.1); color: var(--accent-red); }
.danger-btn { padding: 0 16px; height: 36px; background: var(--accent-red); border: none; border-radius: var(--radius-md); color: #fff; font-size: 13px; cursor: pointer; }
.danger-btn:hover { opacity: 0.9; }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
