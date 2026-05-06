<template>
  <div class="login-wrapper">
    <!-- 左侧品牌展示 -->
    <div class="login-hero">
      <div class="hero-content">
        <div class="hero-logo">
          <div class="logo-icon">CS</div>
        </div>
        <h1 class="hero-title">Smart Customer Service</h1>
        <p class="hero-subtitle">企业级智能客服管理平台</p>
        <div class="hero-features">
          <div class="feature-item">
            <div class="feature-icon">📊</div>
            <div class="feature-text">实时数据分析</div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🤖</div>
            <div class="feature-text">AI智能回复</div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">👥</div>
            <div class="feature-text">团队协作管理</div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">🔒</div>
            <div class="feature-text">企业级安全</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录表单 -->
    <div class="login-form-wrapper">
      <div class="login-form-container">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录您的账户以继续</p>
        </div>

        <el-tabs v-model="loginType" class="login-tabs" stretch>
          <el-tab-pane label="密码登录" name="password" />
          <el-tab-pane label="验证码登录" name="sms" />
        </el-tabs>

        <el-form :model="form" @submit.prevent="handleLogin" class="login-form">
          <el-form-item>
            <el-input 
              v-model="form.phone" 
              placeholder="手机号" 
              prefix-icon="Phone" 
              size="large"
              clearable
              class="form-input"
            />
          </el-form-item>

          <el-form-item v-if="loginType === 'password'" class="form-item-animate">
            <el-input 
              v-model="form.password" 
              type="password" 
              placeholder="密码" 
              prefix-icon="Lock" 
              size="large"
              show-password
              class="form-input"
            />
          </el-form-item>

          <el-form-item v-else class="form-item-animate">
            <el-input 
              v-model="form.code" 
              placeholder="验证码" 
              size="large"
              class="form-input"
            >
              <template #append>
                <el-button 
                  :disabled="countdown > 0" 
                  @click="sendCode" 
                  :loading="sending"
                  class="code-btn"
                >
                  {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                </el-button>
              </template>
            </el-input>
          </el-form-item>

          <el-button 
            type="primary" 
            size="large" 
            native-type="submit" 
            :loading="loading" 
            class="login-btn"
          >
            <span v-if="!loading">立即登录</span>
            <span v-else>登录中...</span>
          </el-button>
        </el-form>

        <div class="form-footer">
          <div class="links">
            <el-button link type="primary" size="small">忘记密码？</el-button>
            <el-divider direction="vertical" />
            <el-button link type="primary" size="small">联系支持</el-button>
          </div>
          <p class="terms">
            登录即表示您已同意<el-button link type="primary" size="small">服务条款</el-button>和<el-button link type="primary" size="small">隐私政策</el-button>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loginType = ref('password')
const loading = ref(false)
const sending = ref(false)
const countdown = ref(0)
const form = reactive({ phone: '', password: '', code: '' })

async function handleLogin() {
  if (!form.phone) {
    ElMessage.warning('请输入手机号')
    return
  }

  if (loginType.value === 'password' && !form.password) {
    ElMessage.warning('请输入密码')
    return
  }

  if (loginType.value === 'sms' && !form.code) {
    ElMessage.warning('请输入验证码')
    return
  }

  loading.value = true
  try {
    if (loginType.value === 'password') {
      await auth.login(form.phone, form.password)
    } else {
      await auth.loginBySms(form.phone, form.code)
    }
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch (error) {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function sendCode() {
  if (!form.phone) {
    ElMessage.warning('请输入手机号')
    return
  }
  
  sending.value = true
  try {
    await auth.sendSms(form.phone)
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (error) {
    // error handled by interceptor
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  height: 100vh;
  background: #f5f7fa;
  overflow: hidden;
}

/* 左侧品牌展示 */
.login-hero {
  flex: 1;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #00a8e8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  position: relative;
  overflow: hidden;
}

.login-hero::before {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
  top: -100px;
  right: -100px;
}

.login-hero::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 50%;
  bottom: -80px;
  left: -80px;
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
}

.hero-logo {
  margin-bottom: 40px;
}

.logo-icon {
  width: 80px;
  height: 80px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: bold;
  margin: 0 auto;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: 0.5px;
}

.hero-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 60px;
}

.hero-features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.feature-icon {
  font-size: 32px;
}

.feature-text {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

/* 右侧登录表单 */
.login-form-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #f5f7fa;
}

.login-form-container {
  width: 100%;
  max-width: 420px;
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.form-header {
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 8px;
}

.form-header p {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.login-tabs {
  margin-bottom: 24px;
}

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
  border-bottom: none;
}

.login-tabs :deep(.el-tabs__nav-wrap) {
  background: #f3f4f6;
  border-radius: 8px;
  padding: 4px;
}

.login-tabs :deep(.el-tabs__item) {
  color: #6b7280;
  font-weight: 500;
  margin: 0 4px;
  border-radius: 6px;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: #1e40af;
  background: white;
}

.login-form {
  margin-bottom: 24px;
}

.form-item-animate {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.form-input :deep(.el-input__wrapper) {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.form-input :deep(.el-input__wrapper:hover) {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.form-input :deep(.el-input__wrapper.is-focus) {
  background: white;
  border-color: #1e40af;
  box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1);
}

.code-btn {
  padding: 0 16px;
  font-weight: 500;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
  border: none;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.login-btn :deep(.el-button__content) {
  letter-spacing: 0.5px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(30, 40, 175, 0.3);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.form-footer {
  text-align: center;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.links {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.links :deep(.el-button) {
  font-size: 13px;
  padding: 0;
}

.links :deep(.el-divider) {
  background-color: #e5e7eb;
  height: 16px;
}

.terms {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
  line-height: 1.5;
}

.terms :deep(.el-button) {
  padding: 0;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .login-hero {
    display: none;
  }

  .login-form-wrapper {
    flex: 1;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #00a8e8 100%);
  }

  .login-form-container {
    background: rgba(255, 255, 255, 0.95);
  }
}

@media (max-width: 768px) {
  .login-wrapper {
    padding: 20px;
  }

  .login-form-container {
    max-width: 100%;
    padding: 30px 20px;
  }

  .hero-title {
    font-size: 24px;
  }

  .form-header h2 {
    font-size: 20px;
  }
}
</style>
