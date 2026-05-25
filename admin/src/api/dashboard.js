import client from './client'

/**
 * 仪表盘模块 API
 */
export const dashboardApi = {
  /**
   * 获取运营概览
   * @param {string} tenantId - 租户ID
   */
  getOverview(tenantId = 'default') {
    return client.get('/api/v1/admin/dashboard/overview', {
      params: { tenant_id: tenantId },
    })
  },

  /**
   * 获取对话趋势
   * @param {string} tenantId - 租户ID
   * @param {number} days - 天数 (1-90)
   */
  getConversationTrend(tenantId = 'default', days = 7) {
    return client.get('/api/v1/admin/dashboard/conversations/trend', {
      params: { tenant_id: tenantId, days },
    })
  },

  /**
   * 获取性能指标
   * @param {string} tenantId - 租户ID
   */
  getPerformance(tenantId = 'default') {
    return client.get('/api/v1/admin/dashboard/performance', {
      params: { tenant_id: tenantId },
    })
  },

  /**
   * 获取活跃用户排行
   * @param {string} tenantId - 租户ID
   * @param {number} limit - 返回数量 (1-100)
   */
  getTopUsers(tenantId = 'default', limit = 10) {
    return client.get('/api/v1/admin/dashboard/users/top', {
      params: { tenant_id: tenantId, limit },
    })
  },

  /**
   * 获取运营报告
   * @param {string} tenantId - 租户ID
   */
  getOperationalReport(tenantId = 'default') {
    return client.get('/api/v1/admin/reports/operational', {
      params: { tenant_id: tenantId },
    })
  },
}

export default dashboardApi
