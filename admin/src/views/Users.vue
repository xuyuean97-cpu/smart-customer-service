<template>
  <div class="users-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h2>用户管理</h2>
        <span class="user-count">共 {{ users.length }} 位用户</span>
      </div>
      <div class="header-right">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input type="text" placeholder="搜索用户..." class="search-input" />
        </div>
        <button class="filter-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="22,3 2,3 10,12.46 10,19 14,21 14,12.46"/>
          </svg>
          筛选
        </button>
      </div>
    </div>

    <!-- Users Grid -->
    <div class="users-grid">
      <div 
        v-for="user in users" 
        :key="user.user_id" 
        class="user-card"
      >
        <div class="user-header">
          <div class="user-avatar">
            {{ user.user_id?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <div class="user-info">
            <h4 class="user-name">{{ user.user_id || '未知用户' }}</h4>
            <span class="user-status online">在线</span>
          </div>
          <button class="more-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="1"/>
              <circle cx="12" cy="5" r="1"/>
              <circle cx="12" cy="19" r="1"/>
            </svg>
          </button>
        </div>
        
        <div class="user-stats">
          <div class="stat-item">
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ user.conversation_count || 0 }}</span>
              <span class="stat-label">对话数</span>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ user.avg_quality || '-' }}</span>
              <span class="stat-label">质量分</span>
            </div>
          </div>
        </div>
        
        <div class="user-actions">
          <button class="action-btn primary" @click="viewProfile(user)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            查看画像
          </button>
          <button class="action-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            历史对话
          </button>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-if="!users.length" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
        <h3>暂无用户数据</h3>
        <p>用户数据将在对话后自动生成</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import client from '../api/client'

const users = ref([])

onMounted(async () => {
  const resp = await client.get('/api/v1/admin/dashboard/users/top?limit=50')
  users.value = resp.data.users || []
})

function formatProfile(profile) {
  if (!profile || Object.keys(profile).length === 0) return null
  const p = profile
  const ca = p.content_analysis || {}
  const si = p.shopping_interaction || {}
  const ua = p.inferred_user_attribute || {}
  const sm = p.session_metrics || {}
  const sections = []

  const attrs = []
  if (ua.customer_type) attrs.push(`<span class="tag blue">${ua.customer_type}</span>`)
  if (ua.role) attrs.push(`<span class="tag green">${ua.role}</span>`)
  if (ua.confidence) attrs.push(`置信度: ${(ua.confidence * 100).toFixed(0)}%`)
  if (attrs.length) sections.push(`<div class="pf-section"><h4>用户画像</h4><div class="pf-tags">${attrs.join(' ')}</div></div>`)

  const contents = []
  if (ca.language) contents.push(`语种: ${ca.language}`)
  if (ca.style) contents.push(`风格: ${ca.style}`)
  if (ca.sentiment) contents.push(`情绪: ${ca.sentiment}`)
  if (ca.satisfaction_score) contents.push(`满意度: ${ca.satisfaction_score}`)
  if (ca.keywords?.length) contents.push(`关键词: ${ca.keywords.slice(0, 8).join(', ')}`)
  if (contents.length) sections.push(`<div class="pf-section"><h4>内容特征</h4><p>${contents.join('<br>')}</p></div>`)

  const shops = []
  if (si.orders?.length) shops.push(`涉及订单: ${si.orders.map(o => o.order_id || o).slice(0, 5).join(', ')}`)
  if (si.product_mentioned) shops.push(`关注商品: ${si.product_mentioned.slice(0, 5).join(', ')}`)
  if (shops.length) sections.push(`<div class="pf-section"><h4>购物行为</h4><p>${shops.join('<br>')}</p></div>`)

  const metrics = []
  if (sm.total_turns) metrics.push(`对话轮次: ${sm.total_turns}`)
  if (sm.avg_response_time) metrics.push(`平均响应: ${sm.avg_response_time}s`)
  if (metrics.length) sections.push(`<div class="pf-section"><h4>会话统计</h4><p>${metrics.join('<br>')}</p></div>`)

  return sections.length
    ? `<div class="profile-card">${sections.join('')}</div>`
    : `<p style="color:var(--text-muted)">画像数据正在生成中，请稍后再试</p>`
}

async function viewProfile(row) {
  try {
    const resp = await client.get(`/memory/v1/profile/${row.user_id}`)
    const profile = resp.data?.profile || resp.data
    const html = formatProfile(profile)
    ElMessageBox.alert(
      html || '<p>暂无画像数据</p>',
      `${row.user_id} 用户画像`,
      {
        dangerouslyUseHTMLString: true,
        customClass: 'profile-dialog',
        confirmButtonText: '关闭',
      }
    )
  } catch {
    ElMessageBox.alert('<p style="color:var(--text-muted)">暂无画像数据，该用户可能尚未产生足够对话</p>', `${row.user_id}`)
  }
}
</script>

<style scoped>
.users-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.user-count {
  font-size: 13px;
  color: var(--text-muted);
  background: var(--bg-secondary);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
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
  width: 220px;
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

.filter-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 38px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.filter-btn svg {
  width: 16px;
  height: 16px;
}

.users-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.user-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.25s ease;
  animation: userCardFadeIn 0.4s ease-out backwards;
}

.users-grid .user-card:nth-child(1) { animation-delay: 0.05s; }
.users-grid .user-card:nth-child(2) { animation-delay: 0.1s; }
.users-grid .user-card:nth-child(3) { animation-delay: 0.15s; }
.users-grid .user-card:nth-child(4) { animation-delay: 0.2s; }
.users-grid .user-card:nth-child(5) { animation-delay: 0.25s; }
.users-grid .user-card:nth-child(6) { animation-delay: 0.3s; }

@keyframes userCardFadeIn {
  from {
    opacity: 0;
    transform: translateY(15px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.user-card:hover {
  border-color: var(--accent-blue);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
  transform: translateY(-4px);
}

.user-card:hover .user-avatar {
  transform: scale(1.1);
}

.user-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 20px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 18px;
  font-weight: 600;
  transition: transform 0.25s ease;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.user-status.online {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.more-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.more-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.more-btn svg {
  width: 18px;
  height: 18px;
}

.user-stats {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 36px;
  height: 36px;
  background: rgba(59, 130, 246, 0.15);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-blue);
}

.stat-icon svg {
  width: 18px;
  height: 18px;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.user-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.action-btn.primary {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
  color: white;
}

.action-btn.primary:hover {
  background: var(--accent-blue-hover);
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  color: var(--text-muted);
}

.empty-state svg {
  width: 56px;
  height: 56px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 8px 0;
}

.empty-state p {
  font-size: 14px;
  margin: 0;
}

/* Profile Dialog */
.profile-card { min-width: 320px; text-align: left; }
.pf-section { margin-bottom: 16px; }
.pf-section h4 { font-size: 13px; font-weight: 600; color: var(--accent-blue); margin: 0 0 8px 0; padding-bottom: 4px; border-bottom: 1px solid var(--border-color); }
.pf-section p { font-size: 13px; color: var(--text-primary); line-height: 1.8; margin: 0; }
.pf-tags { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.tag { display: inline-block; padding: 2px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.tag.blue { background: rgba(59,130,246,0.15); color: var(--accent-blue); }
.tag.green { background: rgba(34,197,94,0.15); color: var(--accent-green); }
</style>
