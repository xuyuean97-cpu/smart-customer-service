import client from './client'

/**
 * 计费模块 API
 */
export const billingApi = {
  /**
   * 获取用量统计
   * @param {string} tenantId - 租户ID
   * @param {number} days - 天数 (1-365)
   */
  getUsage(tenantId = 'default', days = 30) {
    return client.get('/api/v1/admin/billing/usage', {
      params: { tenant_id: tenantId, days },
    })
  },
}

export default billingApi
