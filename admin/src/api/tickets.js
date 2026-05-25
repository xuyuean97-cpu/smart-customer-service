import client from './client'

/**
 * 工单系统模块 API
 */
export const ticketsApi = {
  /**
   * 获取工单列表
   * @param {Object} params - 查询参数
   * @param {string} [params.tenant_id] - 租户ID
   * @param {string} [params.status] - 状态 (open/in_progress/resolved/closed)
   * @param {number} [params.limit] - 返回数量
   */
  list(params = {}) {
    return client.get('/api/v1/tickets', {
      params: { tenant_id: 'default', limit: 100, ...params },
    })
  },

  /**
   * 创建工单
   * @param {Object} data - 工单数据
   * @param {string} data.user_id - 用户ID
   * @param {string} data.summary - 摘要
   * @param {string} [data.priority] - 优先级 (medium/high/urgent)
   * @param {string} [data.tenant_id] - 租户ID
   */
  create(data) {
    return client.post('/api/v1/tickets', {
      tenant_id: 'default',
      priority: 'medium',
      ...data,
    })
  },

  /**
   * 获取单个工单详情
   * @param {string} ticketId - 工单ID
   */
  get(ticketId) {
    return client.get(`/api/v1/tickets/${ticketId}`)
  },

  /**
   * 更新工单
   * @param {string} ticketId - 工单ID
   * @param {Object} data - 更新数据
   * @param {string} [data.status] - 状态
   * @param {string} [data.agent_id] - 坐席ID
   * @param {string} [data.priority] - 优先级
   * @param {string} [data.resolution_note] - 处理备注
   */
  update(ticketId, data) {
    return client.patch(`/api/v1/tickets/${ticketId}`, data)
  },

  /**
   * 创建 WebSocket 连接（实时工单通知）
   * @param {Function} onMessage - 消息回调
   * @param {Function} onError - 错误回调
   * @param {Function} onClose - 关闭回调
   * @returns {Object} - { ws, close }
   */
  connectWebSocket(onMessage, onError, onClose) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/tickets/agent/ws`
    
    let ws = null
    let reconnectTimer = null
    let isManualClose = false

    const connect = () => {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Tickets WebSocket] Connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage?.(data)
        } catch (e) {
          onMessage?.(event.data)
        }
      }

      ws.onerror = (error) => {
        console.error('[Tickets WebSocket] Error:', error)
        onError?.(error)
      }

      ws.onclose = () => {
        console.log('[Tickets WebSocket] Closed')
        onClose?.()
        // 自动重连（非手动关闭时）
        if (!isManualClose) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return {
      ws,
      close: () => {
        isManualClose = true
        clearTimeout(reconnectTimer)
        ws?.close()
      },
    }
  },
}

export default ticketsApi
