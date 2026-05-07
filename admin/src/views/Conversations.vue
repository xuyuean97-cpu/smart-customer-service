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
          <label>租户</label>
          <input 
            v-model="filters.tenant_id" 
            type="text" 
            disabled
            class="filter-input disabled"
          />
        </div>
        <button class="search-btn" @click="loadHistory">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          查询
        </button>
      </div>
    </div>

    <!-- Conversations List -->
    <div class="conversations-list">
      <div class="list-header">
        <h3>对话记录</h3>
        <span class="record-count">共 {{ conversations.length }} 条记录</span>
      </div>
      
      <div class="conversation-items">
        <div 
          v-for="(conv, index) in conversations" 
          :key="index" 
          class="conversation-item"
        >
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
                <span v-if="conv.quality_score" class="quality-badge">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
                  </svg>
                  {{ conv.quality_score }}
                </span>
                <span v-if="conv.user_approved" class="approved-badge">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3z"/>
                    <path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/>
                  </svg>
                  已赞
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
        </div>
        
        <!-- Empty State -->
        <div v-if="!conversations.length" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
          <h3>暂无对话记录</h3>
          <p>尝试调整筛选条件或稍后再试</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import client from '../api/client'

const conversations = ref([])
const filters = reactive({ tenant_id: 'default', user_id: '' })

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return timeStr.slice(0, 19).replace('T', ' ')
}

async function loadHistory() {
  const params = { application_id: '电商主智能客服', limit: 100 }
  if (filters.user_id) params.user_id = filters.user_id
  try {
    const resp = await client.get('/memory/v1/conversations/history', { params })
    conversations.value = resp.data.conversations || []
  } catch {
    conversations.value = []
  }
}
loadHistory()
</script>

<style scoped>
.conversations-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-item label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-input {
  width: 200px;
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

.filter-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
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

.search-btn:hover {
  background: var(--accent-blue-hover);
}

.search-btn svg {
  width: 16px;
  height: 16px;
}

.conversations-list {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.list-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.record-count {
  font-size: 12px;
  color: var(--text-muted);
}

.conversation-items {
  max-height: calc(100vh - 340px);
  overflow-y: auto;
}

.conversation-item {
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.conversation-item:hover {
  background: var(--bg-tertiary);
}

.conversation-item:hover .user-avatar {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.conversation-item:last-child {
  border-bottom: none;
}

.conv-header {
  margin-bottom: 16px;
}

.conv-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
}

.quality-badge, .approved-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}

.quality-badge {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
}

.quality-badge svg {
  width: 12px;
  height: 12px;
}

.approved-badge {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.approved-badge svg {
  width: 12px;
  height: 12px;
}

.conv-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
</style>
