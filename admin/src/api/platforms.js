import client from './client'

export const platformsApi = {
  /** 获取已配置的平台列表 */
  list() {
    return client.get('/api/v1/platforms')
  },

  /** 获取支持的平台类型 */
  supported() {
    return client.get('/api/v1/platforms/supported')
  },

  /** 获取单个平台配置 */
  get(platform) {
    return client.get(`/api/v1/platforms/${platform}`)
  },

  /** 添加新平台 */
  create(data) {
    return client.post('/api/v1/platforms', data)
  },

  /** 更新平台配置 */
  update(platform, data) {
    return client.put(`/api/v1/platforms/${platform}`, data)
  },

  /** 删除平台 */
  remove(platform) {
    return client.delete(`/api/v1/platforms/${platform}`)
  },

  /** 测试平台连接 */
  test(platform) {
    return client.post(`/api/v1/platforms/${platform}/test`)
  },

  /** 获取 OAuth 授权链接 */
  getOAuthUrl(platform) {
    return client.get(`/api/v1/platforms/${platform}/oauth/url`)
  },
}
