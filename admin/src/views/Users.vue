<template>
  <div class="users-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h2>用户管理</h2>
        <span class="user-count">共 {{ filteredUsers.length }} 位用户</span>
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
            placeholder="搜索用户ID..." 
            class="search-input" 
          />
        </div>
        <button class="refresh-btn" @click="loadUsers" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: loading }">
            <path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- Users Grid -->
    <div class="users-grid">
      <div 
        v-for="user in filteredUsers" 
        :key="user.user_id" 
        class="user-card"
      >
        <div class="user-header">
          <div class="user-avatar">
            {{ user.user_id?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <div class="user-info">
            <h4 class="user-name">{{ user.user_id || '未知用户' }}</h4>
            <span class="user-status online">活跃</span>
          </div>
          <div class="user-menu">
            <button class="more-btn" @click="toggleMenu(user.user_id)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="1"/>
                <circle cx="12" cy="5" r="1"/>
                <circle cx="12" cy="19" r="1"/>
              </svg>
            </button>
            <div v-if="activeMenu === user.user_id" class="dropdown-menu">
              <button @click="viewConversations(user)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                </svg>
                查看对话
              </button>
              <button @click="extractUserProfile(user)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/>
                  <path d="M3 3v5h5"/>
                </svg>
                提取画像
              </button>
            </div>
          </div>
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
            <div class="stat-icon quality">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-value">{{ formatQuality(user.avg_quality) }}</span>
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
          <button class="action-btn" @click="viewStats(user)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"/>
              <line x1="12" y1="20" x2="12" y2="4"/>
              <line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
            详细统计
          </button>
        </div>
      </div>
      
      <!-- Loading State -->
      <div v-if="loading && users.length === 0" class="loading-card">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      
      <!-- Empty State -->
      <div v-if="!loading && filteredUsers.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
        <h3>{{ searchQuery ? '未找到匹配用户' : '暂无用户数据' }}</h3>
        <p>{{ searchQuery ? '尝试其他搜索关键词' : '用户数据将在对话后自动生成' }}</p>
      </div>
    </div>

    <!-- Profile Drawer -->
    <el-drawer 
      v-model="profileDrawerVisible" 
      :title="`${currentUser?.user_id || ''} 用户画像`"
      size="480px"
      class="profile-drawer"
    >
      <div v-if="profileLoading" class="drawer-loading">
        <div class="spinner"></div>
        <span>加载画像中...</span>
      </div>
      <div v-else-if="currentProfile" class="profile-content">
        <!-- User Attributes -->
        <div class="profile-section" v-if="currentProfile.inferred_user_attribute">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            用户特征
          </h4>
          <div class="profile-tags">
            <span v-if="currentProfile.inferred_user_attribute.customer_type" class="tag blue">
              {{ currentProfile.inferred_user_attribute.customer_type }}
            </span>
            <span v-if="currentProfile.inferred_user_attribute.role" class="tag green">
              {{ currentProfile.inferred_user_attribute.role }}
            </span>
          </div>
          <div v-if="currentProfile.inferred_user_attribute.confidence" class="confidence-bar">
            <span>置信度</span>
            <div class="bar-container">
              <div class="bar-fill" :style="{ width: (currentProfile.inferred_user_attribute.confidence * 100) + '%' }"></div>
            </div>
            <span>{{ (currentProfile.inferred_user_attribute.confidence * 100).toFixed(0) }}%</span>
          </div>
        </div>

        <!-- Content Analysis -->
        <div class="profile-section" v-if="currentProfile.content_analysis">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            内容分析
          </h4>
          <div class="info-grid">
            <div class="info-item" v-if="currentProfile.content_analysis.language">
              <span class="info-label">语种</span>
              <span class="info-value">{{ currentProfile.content_analysis.language }}</span>
            </div>
            <div class="info-item" v-if="currentProfile.content_analysis.style">
              <span class="info-label">风格</span>
              <span class="info-value">{{ currentProfile.content_analysis.style }}</span>
            </div>
            <div class="info-item" v-if="currentProfile.content_analysis.sentiment">
              <span class="info-label">情绪</span>
              <span class="info-value" :class="getSentimentClass(currentProfile.content_analysis.sentiment)">
                {{ currentProfile.content_analysis.sentiment }}
              </span>
            </div>
            <div class="info-item" v-if="currentProfile.content_analysis.satisfaction_score">
              <span class="info-label">满意度</span>
              <span class="info-value">{{ (currentProfile.content_analysis.satisfaction_score * 100).toFixed(0) }}%</span>
            </div>
          </div>
          <div v-if="currentProfile.content_analysis.keywords?.length" class="keywords-section">
            <span class="info-label">关键词</span>
            <div class="keywords">
              <span v-for="kw in currentProfile.content_analysis.keywords.slice(0, 10)" :key="kw" class="keyword">
                {{ kw }}
              </span>
            </div>
          </div>
        </div>

        <!-- Shopping Interaction -->
        <div class="profile-section" v-if="currentProfile.shopping_interaction">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="21" r="1"/>
              <circle cx="20" cy="21" r="1"/>
              <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6"/>
            </svg>
            购物行为
          </h4>
          <div v-if="currentProfile.shopping_interaction.product_mentioned?.length" class="products-section">
            <span class="info-label">关注商品</span>
            <div class="product-list">
              <span v-for="p in currentProfile.shopping_interaction.product_mentioned.slice(0, 6)" :key="p" class="product-item">
                {{ p }}
              </span>
            </div>
          </div>
          <div v-if="currentProfile.shopping_interaction.orders?.length" class="orders-section">
            <span class="info-label">相关订单</span>
            <div class="order-list">
              <span v-for="o in currentProfile.shopping_interaction.orders.slice(0, 5)" :key="o.order_id || o" class="order-item">
                {{ o.order_id || o }}
              </span>
            </div>
          </div>
        </div>

        <!-- Session Metrics -->
        <div class="profile-section" v-if="currentProfile.session_metrics">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12,6 12,12 16,14"/>
            </svg>
            会话统计
          </h4>
          <div class="info-grid">
            <div class="info-item" v-if="currentProfile.session_metrics.total_turns">
              <span class="info-label">对话轮次</span>
              <span class="info-value">{{ currentProfile.session_metrics.total_turns }}</span>
            </div>
            <div class="info-item" v-if="currentProfile.session_metrics.duration_seconds">
              <span class="info-label">会话时长</span>
              <span class="info-value">{{ formatDuration(currentProfile.session_metrics.duration_seconds) }}</span>
            </div>
          </div>
        </div>

        <!-- Technical Context -->
        <div class="profile-section" v-if="currentProfile.technical_context">
          <h4>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
              <line x1="12" y1="18" x2="12.01" y2="18"/>
            </svg>
            技术信息
          </h4>
          <div class="info-grid">
            <div class="info-item" v-if="currentProfile.technical_context.source">
              <span class="info-label">来源</span>
              <span class="info-value">{{ currentProfile.technical_context.source }}</span>
            </div>
            <div class="info-item" v-if="currentProfile.technical_context.device">
              <span class="info-label">设备</span>
              <span class="info-value">{{ currentProfile.technical_context.device }}</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="drawer-actions">
          <button class="action-btn primary" @click="viewConversations(currentUser)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            查看历史对话
          </button>
          <button class="action-btn" @click="extractUserProfile(currentUser)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
            </svg>
            重新提取
          </button>
        </div>
      </div>
      <div v-else class="drawer-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p>暂无画像数据</p>
        <button class="action-btn primary" @click="extractUserProfile(currentUser)">
          立即提取画像
        </button>
      </div>
    </el-drawer>

    <!-- Stats Dialog -->
    <el-dialog v-model="statsDialogVisible" :title="`${currentUser?.user_id || ''} 详细统计`" width="520px">
      <div v-if="statsLoading" class="dialog-loading">
        <div class="spinner"></div>
        <span>加载统计数据...</span>
      </div>
      <div v-else-if="currentStats" class="stats-content">
        <div class="stats-grid">
          <div class="stats-card">
            <div class="stats-icon blue">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
              </svg>
            </div>
            <div class="stats-info">
              <span class="stats-value">{{ currentStats.total_conversations || 0 }}</span>
              <span class="stats-label">总对话数</span>
            </div>
          </div>
          <div class="stats-card">
            <div class="stats-icon green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
              </svg>
            </div>
            <div class="stats-info">
              <span class="stats-value">{{ formatQuality(currentStats.avg_quality_score) }}</span>
              <span class="stats-label">平均质量分</span>
            </div>
          </div>
          <div class="stats-card">
            <div class="stats-icon purple">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3z"/>
              </svg>
            </div>
            <div class="stats-info">
              <span class="stats-value">{{ currentStats.total_likes || 0 }}</span>
              <span class="stats-label">获得点赞</span>
            </div>
          </div>
          <div class="stats-card">
            <div class="stats-icon cyan">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12,6 12,12 16,14"/>
              </svg>
            </div>
            <div class="stats-info">
              <span class="stats-value">{{ currentStats.first_seen ? currentStats.first_seen.slice(0, 10) : '-' }}</span>
              <span class="stats-label">首次活跃</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="dialog-empty">
        <p>暂无统计数据</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usersApi } from '../api'

const router = useRouter()

const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const activeMenu = ref(null)

// Profile drawer
const profileDrawerVisible = ref(false)
const profileLoading = ref(false)
const currentUser = ref(null)
const currentProfile = ref(null)

// Stats dialog
const statsDialogVisible = ref(false)
const statsLoading = ref(false)
const currentStats = ref(null)

const filteredUsers = computed(() => {
  if (!searchQuery.value.trim()) return users.value
  const q = searchQuery.value.toLowerCase()
  return users.value.filter(u => 
    u.user_id?.toLowerCase().includes(q)
  )
})

function formatQuality(score) {
  if (!score && score !== 0) return '-'
  return (score * 100).toFixed(0) + '%'
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  return `${Math.floor(seconds / 3600)}小时`
}

function getSentimentClass(sentiment) {
  if (!sentiment) return ''
  const s = sentiment.toLowerCase()
  if (s.includes('positive') || s === 'positive') return 'positive'
  if (s.includes('negative') || s === 'negative') return 'negative'
  return 'neutral'
}

function toggleMenu(userId) {
  activeMenu.value = activeMenu.value === userId ? null : userId
}

// Close menu when clicking outside
function handleClickOutside(e) {
  if (!e.target.closest('.user-menu')) {
    activeMenu.value = null
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  loadUsers()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function loadUsers() {
  loading.value = true
  try {
    const resp = await usersApi.getTopUsers('default', 50)
    users.value = resp.data.users || []
  } catch (e) {
    ElMessage.error('加载用户失败')
    users.value = []
  } finally {
    loading.value = false
  }
}

async function viewProfile(user) {
  currentUser.value = user
  currentProfile.value = null
  profileDrawerVisible.value = true
  profileLoading.value = true
  
  try {
    const resp = await usersApi.getProfile(user.user_id)
    currentProfile.value = resp.data?.profile || resp.data || null
  } catch (e) {
    currentProfile.value = null
  } finally {
    profileLoading.value = false
  }
}

async function viewStats(user) {
  currentUser.value = user
  currentStats.value = null
  statsDialogVisible.value = true
  statsLoading.value = true
  
  try {
    const resp = await usersApi.getStats(user.user_id)
    currentStats.value = resp.data || null
  } catch (e) {
    currentStats.value = null
  } finally {
    statsLoading.value = false
  }
}

async function extractUserProfile(user) {
  activeMenu.value = null
  try {
    await usersApi.extractProfile(user.user_id)
    ElMessage.success('画像提取已触发，请稍后刷新查看')
  } catch (e) {
    ElMessage.error('提取失败: ' + (e.message || '未知错误'))
  }
}

function viewConversations(user) {
  activeMenu.value = null
  profileDrawerVisible.value = false
  router.push({ path: '/conversations', query: { user_id: user.user_id } })
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

.refresh-btn {
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

.refresh-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.refresh-btn svg {
  width: 16px;
  height: 16px;
}

.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
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

.user-menu {
  position: relative;
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

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  z-index: 100;
  min-width: 140px;
  overflow: hidden;
}

.dropdown-menu button {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.dropdown-menu button:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.dropdown-menu button svg {
  width: 14px;
  height: 14px;
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

.stat-icon.quality {
  background: rgba(234, 179, 8, 0.15);
  color: var(--accent-yellow);
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

/* Loading & Empty States */
.loading-card, .empty-state {
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

.loading-card {
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

/* Profile Drawer */
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.profile-section h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.profile-section h4 svg {
  width: 18px;
  height: 18px;
  color: var(--accent-blue);
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.tag.blue {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}

.tag.green {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.confidence-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

.bar-container {
  flex: 1;
  height: 6px;
  background: var(--bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan));
  border-radius: 3px;
  transition: width 0.3s ease;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
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
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 13px;
  color: var(--text-primary);
}

.info-value.positive {
  color: var(--accent-green);
}

.info-value.negative {
  color: var(--accent-red);
}

.info-value.neutral {
  color: var(--accent-yellow);
}

.keywords-section, .products-section, .orders-section {
  margin-top: 12px;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.keyword {
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-secondary);
}

.product-list, .order-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.product-item {
  padding: 4px 10px;
  background: rgba(34, 197, 94, 0.1);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--accent-green);
}

.order-item {
  padding: 4px 10px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-family: monospace;
  color: var(--accent-blue);
}

.drawer-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.drawer-loading, .drawer-empty, .dialog-loading, .dialog-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-muted);
  gap: 12px;
}

.drawer-empty svg {
  width: 48px;
  height: 48px;
  opacity: 0.5;
  margin-bottom: 8px;
}

/* Stats Dialog */
.stats-content {
  padding: 8px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.stats-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.stats-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
}

.stats-icon svg {
  width: 22px;
  height: 22px;
}

.stats-icon.blue {
  background: rgba(59, 130, 246, 0.15);
  color: var(--accent-blue);
}

.stats-icon.green {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.stats-icon.purple {
  background: rgba(168, 85, 247, 0.15);
  color: var(--accent-purple);
}

.stats-icon.cyan {
  background: rgba(6, 182, 212, 0.15);
  color: var(--accent-cyan);
}

.stats-info {
  display: flex;
  flex-direction: column;
}

.stats-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.stats-label {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
