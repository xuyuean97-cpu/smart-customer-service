<template>
  <div class="login-bg">
    <div class="login-card">
      <h1>电商智能客服</h1>
      <p>管理后台</p>
      <el-tabs v-model="loginType" class="login-tabs">
        <el-tab-pane label="密码登录" name="password" />
        <el-tab-pane label="验证码登录" name="sms" />
      </el-tabs>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.phone" placeholder="手机号" prefix-icon="Phone" size="large" />
        </el-form-item>
        <el-form-item v-if="loginType === 'password'">
          <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" size="large" show-password />
        </el-form-item>
        <el-form-item v-else>
          <el-input v-model="form.code" placeholder="验证码" size="large">
            <template #append>
              <el-button :disabled="countdown > 0" @click="sendCode" :loading="sending">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" native-type="submit" :loading="loading" class="login-btn">
          登 录
        </el-button>
      </el-form>
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
  loading.value = true
  try {
    if (loginType.value === 'password') {
      await auth.login(form.phone, form.password)
    } else {
      await auth.loginBySms(form.phone, form.code)
    }
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function sendCode() {
  if (!form.phone) return ElMessage.warning('请输入手机号')
  sending.value = true
  try {
    await auth.sendSms(form.phone)
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => { countdown.value--; if (countdown.value <= 0) clearInterval(timer) }, 1000)
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.login-bg { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.login-card { width: 400px; background: #fff; border-radius: 12px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,.15); }
.login-card h1 { text-align: center; font-size: 24px; color: #303133; margin-bottom: 4px; }
.login-card p { text-align: center; color: #909399; margin-bottom: 24px; }
.login-tabs { margin-bottom: 16px; }
.login-btn { width: 100%; }
</style>
