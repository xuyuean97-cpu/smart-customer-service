import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('admin_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  async function login(phone, password) {
    const resp = await authApi.login(phone, password)
    token.value = resp.data.access_token
    user.value = { phone: resp.data.phone || phone, username: resp.data.username }
    localStorage.setItem('admin_token', token.value)
    localStorage.setItem('admin_user', JSON.stringify(user.value))
    return resp.data
  }

  async function loginBySms(phone, code) {
    const resp = await authApi.loginBySms(phone, code)
    token.value = resp.data.access_token
    user.value = { phone, username: resp.data.username }
    localStorage.setItem('admin_token', token.value)
    localStorage.setItem('admin_user', JSON.stringify(user.value))
    return resp.data
  }

  async function sendSms(phone) {
    await authApi.sendSms(phone)
  }

  async function changePassword(phone, oldPassword, newPassword) {
    await authApi.changePassword(phone, oldPassword, newPassword)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
    router.push('/login')
  }

  return { 
    token, 
    user, 
    isLoggedIn, 
    login, 
    loginBySms, 
    sendSms, 
    changePassword,
    logout 
  }
})
