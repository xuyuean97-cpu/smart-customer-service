import client from './client'

/**
 * 对话历史模块 API
 */
export const conversationsApi = {
  /**
   * 获取对话历史
   * @param {Object} params - 查询参数
   * @param {string} [params.user_id] - 用户ID
   * @param {string} [params.agent_id] - 智能体ID
   * @param {string} [params.run_id] - 会话ID
   * @param {string} [params.application_id] - 应用ID
   * @param {string} [params.start_date] - 开始日期 YYYY-MM-DD
   * @param {string} [params.end_date] - 结束日期 YYYY-MM-DD
   * @param {number} [params.limit] - 返回数量
   */
  getHistory(params = {}) {
    const queryParams = {
      application_id: '电商主智能客服',
      limit: 100,
      ...params,
    }
    // 过滤空值
    Object.keys(queryParams).forEach(key => {
      if (!queryParams[key]) delete queryParams[key]
    })
    return client.get('/memory/v1/conversations/history', { params: queryParams })
  },

  /**
   * 搜索对话
   * @param {string} query - 搜索关键词
   * @param {Object} params - 其他参数
   */
  search(query, params = {}) {
    return client.get('/memory/v1/conversations/search', {
      params: { query, ...params },
    })
  },

  /**
   * 专家审核
   * @param {Object} data - 审核数据
   * @param {string} data.memory_id - 对话记录ID
   * @param {number} data.expert_score - 专家评分 (0-1)
   * @param {string} [data.expert_feedback] - 专家反馈
   */
  expertReview(data) {
    return client.post('/memory/v1/conversations/expert-review', data)
  },

  /**
   * 批量专家审核
   * @param {Array} reviews - 审核数据数组
   */
  batchExpertReview(items) {
    return client.post('/memory/v1/conversations/batch-expert-review', { review_items: items })
  },

  /**
   * 智能过滤
   * @param {Object} filters - 过滤条件
   */
  smartFilter(filters) {
    return client.post('/memory/v1/conversations/smart-filter', filters)
  },

  /**
   * 用户反馈（点赞/点踩）
   * @param {string} response - AI回复内容
   * @param {number} userApproved - 1=点赞, 0=点踩
   */
  userFeedback(response, userApproved) {
    return client.post('/memory/v1/conversations/user-feedback', {
      response,
      user_approved: userApproved,
    })
  },

  /**
   * 导出对话为CSV（前端生成）
   * @param {Array} conversations - 对话数据数组
   * @param {string} filename - 文件名
   */
  exportToCsv(conversations, filename = 'conversations.csv') {
    const headers = ['用户ID', '问题', '回复', '质量评分', '用户点赞', '创建时间']
    const rows = conversations.map(conv => [
      conv.user_id || '',
      `"${(conv.query || '').replace(/"/g, '""')}"`,
      `"${(conv.response || '').replace(/"/g, '""')}"`,
      conv.quality_score || '',
      conv.user_approved || 0,
      conv.created_at || '',
    ])
    
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const BOM = '\uFEFF'
    const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  },
}

export default conversationsApi
