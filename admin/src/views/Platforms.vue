<template>
  <div class="platforms-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-info">
        <h2>第三方平台对接</h2>
        <p>管理电商平台接入配置，支持京东、淘宝、拼多多、抖音等平台</p>
      </div>
      <button class="primary-btn" @click="openAddDialog">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        添加平台
      </button>
    </div>

    <!-- Platform Cards Grid -->
    <div class="platforms-grid" v-if="platforms.length > 0">
      <div class="platform-card" v-for="item in platforms" :key="item.platform">
        <div class="card-header">
          <div class="platform-icon" :class="item.platform">
            <span>{{ getPlatformInitial(item.platform) }}</span>
          </div>
          <div class="platform-info">
            <h3>{{ item.name || item.platform }}</h3>
            <span class="platform-id">{{ item.shop_name || item.shop_id || '未设置店铺' }}</span>
          </div>
          <div class="status-badge" :class="{ active: item.is_active }">
            {{ item.is_active ? '已启用' : '已禁用' }}
          </div>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">App Key</span>
            <span class="value">{{ item.app_key || '***' }}</span>
          </div>
          <div class="info-row" v-if="item.updated_at">
            <span class="label">更新时间</span>
            <span class="value">{{ formatTime(item.updated_at) }}</span>
          </div>
        </div>
        <div class="card-actions">
          <button class="action-btn primary" @click="startOAuth(item.platform)" v-if="!item.access_token">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/>
              <polyline points="10,17 15,12 10,7"/>
              <line x1="15" y1="12" x2="3" y2="12"/>
            </svg>
            授权
          </button>
          <button class="action-btn" @click="testConnection(item.platform)" :disabled="testing === item.platform">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
            {{ testing === item.platform ? '测试中...' : '测试连接' }}
          </button>
          <button class="action-btn" @click="openEditDialog(item)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            编辑
          </button>
          <button class="action-btn danger" @click="confirmDelete(item)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3,6 5,6 21,6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div class="empty-state" v-else-if="!loading">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="empty-icon">
        <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
      </svg>
      <h3>暂无平台接入</h3>
      <p>添加第三方电商平台，让智能客服处理多平台订单和消息</p>
      <button class="primary-btn" @click="openAddDialog">添加第一个平台</button>
    </div>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑平台配置' : '添加平台'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-width="100px" label-position="top">
        <el-form-item label="平台类型" v-if="!isEdit">
          <el-select v-model="form.platform" placeholder="选择平台" style="width: 100%">
            <el-option
              v-for="p in supportedPlatforms"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="平台类型" v-else>
          <el-input :value="getPlatformName(form.platform)" disabled />
        </el-form-item>
        <el-form-item label="App Key">
          <el-input v-model="form.app_key" placeholder="应用 Key" />
        </el-form-item>
        <el-form-item label="App Secret">
          <el-input v-model="form.app_secret" placeholder="应用 Secret" type="password" show-password />
        </el-form-item>
        <el-form-item label="店铺 ID">
          <el-input v-model="form.shop_id" placeholder="店铺 ID（可选）" />
        </el-form-item>
        <el-form-item label="店铺名称">
          <el-input v-model="form.shop_name" placeholder="店铺名称（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :disabled="submitting">
          {{ submitting ? '提交中...' : (isEdit ? '保存' : '添加') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { platformsApi } from '../api'

const platforms = ref([])
const supportedPlatforms = ref([])
const loading = ref(false)
const testing = ref(null)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)

const form = reactive({
  platform: '',
  app_key: '',
  app_secret: '',
  shop_id: '',
  shop_name: '',
})

const platformNames = {
  jd: '京东',
  taobao: '淘宝',
  pdd: '拼多多',
  douyin: '抖音',
}

function getPlatformName(id) {
  return platformNames[id] || id
}

function getPlatformInitial(platform) {
  const names = { jd: '京', taobao: '淘', pdd: '拼', douyin: '抖' }
  return names[platform] || platform.charAt(0).toUpperCase()
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN')
}

async function loadPlatforms() {
  loading.value = true
  try {
    const resp = await platformsApi.list()
    platforms.value = resp.data || []
  } catch (e) {
    ElMessage.error('加载平台列表失败')
  } finally {
    loading.value = false
  }
}

async function loadSupported() {
  try {
    const resp = await platformsApi.supported()
    supportedPlatforms.value = resp.data || []
  } catch {
    supportedPlatforms.value = [
      { id: 'jd', name: '京东' },
      { id: 'taobao', name: '淘宝' },
      { id: 'pdd', name: '拼多多' },
      { id: 'douyin', name: '抖音' },
    ]
  }
}

function openAddDialog() {
  isEdit.value = false
  form.platform = ''
  form.app_key = ''
  form.app_secret = ''
  form.shop_id = ''
  form.shop_name = ''
  dialogVisible.value = true
}

async function openEditDialog(item) {
  isEdit.value = true
  try {
    const resp = await platformsApi.get(item.platform)
    const data = resp.data
    form.platform = data.platform
    form.app_key = data.app_key
    form.app_secret = data.app_secret
    form.shop_id = data.shop_id || ''
    form.shop_name = data.shop_name || ''
  } catch {
    form.platform = item.platform
    form.app_key = ''
    form.app_secret = ''
    form.shop_id = item.shop_id || ''
    form.shop_name = item.shop_name || ''
  }
  dialogVisible.value = true
}

async function submitForm() {
  if (!form.platform) {
    ElMessage.warning('请选择平台类型')
    return
  }
  if (!form.app_key || !form.app_secret) {
    ElMessage.warning('请填写 App Key 和 App Secret')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value) {
      await platformsApi.update(form.platform, {
        app_key: form.app_key,
        app_secret: form.app_secret,
        shop_id: form.shop_id,
        shop_name: form.shop_name,
      })
      ElMessage.success('更新成功')
    } else {
      await platformsApi.create({
        platform: form.platform,
        app_key: form.app_key,
        app_secret: form.app_secret,
        shop_id: form.shop_id,
        shop_name: form.shop_name,
      })
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    await loadPlatforms()
  } catch (e) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${item.name || item.platform} 平台配置吗？删除后该平台的消息和订单将无法自动处理。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await platformsApi.remove(item.platform)
    ElMessage.success('删除成功')
    await loadPlatforms()
  } catch {
    // cancelled
  }
}

async function testConnection(platform) {
  testing.value = platform
  try {
    const resp = await platformsApi.test(platform)
    const data = resp.data
    if (data.status === 'ok') {
      ElMessage.success('连接测试成功')
    } else if (data.status === 'degraded') {
      ElMessage.warning(resp.message || '连接异常')
    } else {
      ElMessage.info(resp.message || '测试完成')
    }
  } catch (e) {
    ElMessage.error('测试失败: ' + (e.message || '未知错误'))
  } finally {
    testing.value = null
  }
}

async function startOAuth(platform) {
  try {
    const resp = await platformsApi.getOAuthUrl(platform)
    const url = resp.data?.url
    if (url) {
      // 在新窗口打开授权页面
      window.open(url, '_blank', 'width=800,height=600')
      ElMessage.info('请在弹出的窗口中完成授权')
    } else {
      ElMessage.error('获取授权链接失败')
    }
  } catch (e) {
    ElMessage.error('获取授权链接失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => {
  loadPlatforms()
  loadSupported()
})
</script>

<style scoped>
.platforms-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-info h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.header-info p {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.primary-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  height: 40px;
  background: var(--accent-blue);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.primary-btn:hover { background: var(--accent-blue-hover); }
.primary-btn svg { width: 18px; height: 18px; }

/* Cards Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.platform-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all 0.2s ease;
}

.platform-card:hover {
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 0;
}

.platform-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.platform-icon.jd { background: linear-gradient(135deg, #e2231a, #ff6b35); }
.platform-icon.taobao { background: linear-gradient(135deg, #ff6a00, #ff9500); }
.platform-icon.pdd { background: linear-gradient(135deg, #e02e24, #ff4757); }
.platform-icon.douyin { background: linear-gradient(135deg, #25f4ee, #fe2c55); }

.platform-info {
  flex: 1;
  min-width: 0;
}

.platform-info h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.platform-id {
  font-size: 12px;
  color: var(--text-muted);
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 12px;
  background: rgba(161, 161, 170, 0.15);
  color: var(--text-muted);
}

.status-badge.active {
  background: rgba(34, 197, 94, 0.15);
  color: var(--accent-green);
}

.card-body {
  padding: 16px 20px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.info-row .label {
  font-size: 12px;
  color: var(--text-muted);
}

.info-row .value {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-tertiary);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 32px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-btn.danger:hover {
  background: rgba(239, 68, 68, 0.1);
  color: var(--accent-red);
  border-color: rgba(239, 68, 68, 0.3);
}

.action-btn.primary {
  background: var(--accent-blue);
  color: white;
  border-color: var(--accent-blue);
}

.action-btn.primary:hover {
  background: var(--accent-blue-hover);
}

.action-btn svg { width: 14px; height: 14px; }

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--text-muted);
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.empty-state p {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 24px 0;
}
</style>
