import client from './client'

/**
 * 认证模块 API
 */
export const authApi = {
  /**
   * 密码登录
   * @param {string} phone - 手机号
   * @param {string} password - 密码
   */
  login(phone, password) {
    return client.post('/api/auth/login', {
      phone,
      password,
      login_type: 'password',
    })
  },

  /**
   * 验证码登录
   * @param {string} phone - 手机号
   * @param {string} code - 验证码
   */
  loginBySms(phone, code) {
    return client.post('/api/auth/login', {
      phone,
      code,
      login_type: 'code',
    })
  },

  /**
   * 发送短信验证码
   * @param {string} phone - 手机号
   */
  sendSms(phone) {
    return client.post('/api/auth/send-sms', { phone })
  },

  /**
   * 注册
   * @param {string} phone - 手机号
   * @param {string} code - 验证码
   * @param {string} password - 密码
   */
  register(phone, code, password) {
    return client.post('/api/auth/register', { phone, code, password })
  },

  /**
   * 重置密码
   * @param {string} phone - 手机号
   * @param {string} code - 验证码
   * @param {string} newPassword - 新密码
   */
  resetPassword(phone, code, newPassword) {
    return client.post('/api/auth/reset-password', {
      phone,
      code,
      new_password: newPassword,
    })
  },

  /**
   * 修改密码
   * @param {string} phone - 手机号
   * @param {string} oldPassword - 旧密码
   * @param {string} newPassword - 新密码
   */
  changePassword(phone, oldPassword, newPassword) {
    return client.post('/api/auth/change-password', {
      phone,
      old_password: oldPassword,
      new_password: newPassword,
    })
  },
}

export default authApi
