/**
 * 智能客服管理后台 API 服务层
 * 统一管理所有 API 调用
 */

export { default as client } from './client'
export { authApi } from './auth'
export { dashboardApi } from './dashboard'
export { conversationsApi } from './conversations'
export { usersApi } from './users'
export { ticketsApi } from './tickets'
export { billingApi } from './billing'
export { healthApi } from './health'
export { platformsApi } from './platforms'

// 便捷默认导出
import authApi from './auth'
import dashboardApi from './dashboard'
import conversationsApi from './conversations'
import usersApi from './users'
import ticketsApi from './tickets'
import billingApi from './billing'
import healthApi from './health'
import { platformsApi } from './platforms'

export default {
  auth: authApi,
  dashboard: dashboardApi,
  conversations: conversationsApi,
  users: usersApi,
  tickets: ticketsApi,
  billing: billingApi,
  health: healthApi,
  platforms: platformsApi,
}
