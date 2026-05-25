import client from './client'

/**
 * 用户管理模块 API
 */
export const usersApi = {
  /**
   * 获取活跃用户列表
   * @param {string} tenantId - 租户ID
   * @param {number} limit - 返回数量
   */
  getTopUsers(tenantId = 'default', limit = 50) {
    return client.get('/api/v1/admin/dashboard/users/top', {
      params: { tenant_id: tenantId, limit },
    })
  },

  /**
   * 获取用户画像
   * @param {string} userId - 用户ID
   */
  getProfile(userId) {
    return client.get(`/memory/v1/profile/${userId}`)
  },

  /**
   * 触发用户画像提取
   * @param {string} userId - 用户ID
   * @param {string} applicationId - 应用ID
   */
  extractProfile(userId, applicationId = '电商主智能客服') {
    return client.post(`/memory/v1/profile/${userId}/extract`, {
      application_id: applicationId,
    })
  },

  /**
   * 获取用户统计
   * @param {string} userId - 用户ID
   */
  getStats(userId) {
    return client.get(`/memory/v1/stats/${userId}`)
  },
}

export default usersApi
