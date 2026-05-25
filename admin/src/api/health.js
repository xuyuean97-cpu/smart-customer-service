import client from './client'

/**
 * 健康检查模块 API
 */
export const healthApi = {
  /**
   * 获取系统健康状态
   * @returns {Promise<{
   *   status: 'ok' | 'degraded' | 'down',
   *   uptime_seconds: number,
   *   checks: {
   *     postgres: { status: string, latency_ms: number },
   *     chromadb: { status: string, circuit: { healthy: boolean, circuit_open: boolean } },
   *     llm: { status: string, model: string },
   *     redis: { status: string }
   *   }
   * }>}
   */
  check() {
    return client.get('/health')
  },
}

export default healthApi
