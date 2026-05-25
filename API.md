# 智能客服系统 API 文档

Base URL: `http://localhost:8081`

## 通用约定

**响应格式（两种）：**

| 类型 | 格式 | 来源 |
|------|------|------|
| `api/response.py` 统一格式 | `{"code": 0, "message": "ok", "data": {...}}` | Dashboard / Ticket / Billing |
| Memory API 格式 | `{"ret_code": "000000", "ret_msg": "success", "data": {...}}` | 对话历史 / 用户画像 |
| Auth 直接返回 | `{"access_token": "...", ...}` | 登录 / 注册 |

- `code=0` / `ret_code="000000"` 表示成功
- 前端应同时兼容两种格式，自动提取 `data` 字段
- Memory API 的 `data.conversations` 中每条记录字段都在顶层（无 `metadata` 嵌套）

**认证：**
- 管理后台：`Authorization: Bearer <jwt_token>`（需 role=admin 或 agent）
- 外部 API：`X-API-Key: <api_key>`

---

## 1. 认证模块 `/api/auth`

### POST `/api/auth/login`
登录（密码或验证码）。

**请求：** `LoginRequest`
```json
{
  "phone": "13800000001",      // 必填，11位手机号
  "password": "admin",         // 密码登录时必填
  "code": "123456",            // 验证码登录时必填
  "login_type": "password"     // 必填，"password" | "code"
}
```

**响应：** `TokenResponse`
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user_id": "a40452a7-...",
  "username": "admin"
}
```

### POST `/api/auth/register`
注册（需短信验证码）。

```json
{ "phone": "13800000001", "code": "123456", "password": "123456" }
```

### POST `/api/auth/send-sms`
发送短信验证码。
```json
{ "phone": "13800000001" }
```

### POST `/api/auth/reset-password`
重置密码。
```json
{ "phone": "13800000001", "code": "123456", "new_password": "123456" }
```

### POST `/api/auth/change-password`
修改密码。
```json
{ "phone": "13800000001", "old_password": "123456", "new_password": "654321" }
```

---

## 2. 运营仪表盘 `/api/v1/admin`

**全部需要 JWT token（role=admin/agent）**

### GET `/api/v1/admin/dashboard/overview`
运营概览。

**参数：** `?tenant_id=default`

**响应 data 字段：**
```
tenant_id, total_conversations, active_users_today, avg_quality_score, resolution_rate, human_transfer_rate
```

### GET `/api/v1/admin/dashboard/conversations/trend`
对话趋势。

**参数：** `?tenant_id=default&days=7`（1-90 天）

**响应 data 字段：**
```json
{
  "tenant_id": "default",
  "days": 7,
  "points": [{"date": "2026-04-28", "count": 13, "avg_quality": 0.0}, ...]
}
```

### GET `/api/v1/admin/dashboard/performance`
性能指标。

**参数：** `?tenant_id=default`

**响应 data 字段：**
```
resolution_rate, human_transfer_rate, avg_quality_score, total_conversations, avg_response_length
```

### GET `/api/v1/admin/dashboard/users/top`
活跃用户排行。

**参数：** `?tenant_id=default&limit=10`（1-100）

**响应 data 字段：**
```json
{
  "tenant_id": "default",
  "limit": 10,
  "users": [{"user_id": "user_10001", "conversation_count": 21, "avg_quality": 0.0}, ...]
}
```

### GET `/api/v1/admin/reports/operational`
运营报告（复用 OperationalAnalyticsEngine）。

**参数：** `?tenant_id=default`

### GET `/api/v1/admin/billing/usage`
用量统计。

**参数：** `?tenant_id=default&days=30`（1-365）

**响应 data 字段：**
```json
{
  "tenant_id": "default",
  "total_tokens_in": 0,
  "total_tokens_out": 0,
  "total_requests": 0,
  "by_model": {"qwen-plus": 1234},
  "by_date": [{"date": "2026-04-28", "tokens": 500, "requests": 10}, ...]
}
```

---

## 3. 对话记忆 `/memory/v1`

**需要 JWT token（role=admin/agent）**

### GET `/memory/v1/conversations/history`
查询对话历史。**必须提供至少一个筛选参数。**

**参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID |
| `agent_id` | string | 智能体 ID |
| `run_id` | string | 会话 ID |
| `application_id` | string | 应用 ID（推荐 "电商主智能客服"） |
| `limit` | int | 返回数量，默认 50 |
| `start_date` | string | 开始日期 YYYY-MM-DD |
| `end_date` | string | 结束日期 YYYY-MM-DD |

**响应 data 字段：**
```json
{
  "total_count": 25,
  "conversations": [
    {
      "memory_id": "6c64c8a2-...",
      "user_id": "user_10001",
      "application_id": "电商主智能客服",
      "agent_id": "电商主智能客服",
      "run_id": "...",
      "query": "你们店里有便携显示器吗？",
      "response": "亲，有的呢！...",
      "quality_score": 0.85,
      "user_approved": 0,
      "query_source": "微信小程序",
      "query_device": "iPhone 15 Pro",
      "created_at": "2026-04-22T...",
      "updated_at": "2026-04-22T..."
    }
  ],
  "query_params": {...}
}
```

> 注意：对话记录的字段都在**顶层**，不在 `metadata` 里。
> 显示问题用 `conv.query`，显示回复用 `conv.response`。

### POST `/memory/v1/conversations/inject-batch`
批量注入测试对话（仅开发环境）。

**请求：**
```json
{
  "user_id": "user_10001",
  "application_id": "电商主智能客服",
  "tenant_id": "default",
  "messages": [
    {"query": "你好", "response": "亲，你好呀", "quality_score": 0.8, "days_ago": 0}
  ]
}
```

### POST `/memory/v1/conversations/expert-review`
专家审核对话。`ExpertReviewRequest`

### POST `/memory/v1/conversations/batch-expert-review`
批量专家审核。

### POST `/memory/v1/conversations/smart-filter`
智能过滤对话。`SmartFilterRequest`

### POST `/memory/v1/conversations/user-feedback`
用户反馈（点赞/点踩）。
```json
{"response": "AI的回复内容...", "user_approved": 1}
```

### POST `/memory/v1/examples/search`
搜索专家示例。

### GET `/memory/v1/conversations/search`
搜索对话。

### GET `/memory/v1/profile/{user_id}`
获取用户画像。

**响应 data 字段：**
```json
{
  "profile": {
    "session_metrics": {"start_time": "...", "day": "2026-05-06", "duration_seconds": ...},
    "content_analysis": {"language": "中文", "style": "实用型", "sentiment": "neutral", "keywords": [...], "satisfaction_score": 0.72},
    "shopping_interaction": {"orders": [...], "product_mentioned": ["便携显示器", "蓝牙耳机"]},
    "inferred_user_attribute": {"customer_type": "老客", "role": "便携需求用户", "confidence": 0.95},
    "technical_context": {"source": "微信小程序", "device": "iPhone 15 Pro"}
  }
}
```

### POST `/memory/v1/profile/{user_id}/extract`
触发画像提取。

**请求：** `{"application_id": "电商主智能客服"}`

### GET `/memory/v1/stats/{user_id}`
获取用户统计。

---

## 4. 工单系统 `/api/v1/tickets`

### POST `/api/v1/tickets`
创建工单。
```json
{"user_id": "user_10001", "summary": "商品屏幕漏光，要求退换货", "priority": "high", "tenant_id": "default"}
```

### GET `/api/v1/tickets`
查询工单列表。
**参数：** `?tenant_id=default&status=open&limit=20`

### GET `/api/v1/tickets/{ticket_id}`
查询单个工单。

### PATCH `/api/v1/tickets/{ticket_id}`
更新工单。
```json
{"status": "in_progress", "agent_id": "agent_001", "priority": "high"}
```

### WS `/api/v1/tickets/agent/ws`
客服 WebSocket（实时工单通知）。

---

## 5. 聊天接口

### POST `/api/v1/question-recommend/questions`
问题推荐（"猜你想问"）。

**请求：** `QuestionRecommendRequest`
```json
{"thread_id": "...", "user_id": "user_10001", "query": "售后政策"}
```

**响应：**
```json
{"ret_code": "000000", "ret_msg": "success", "item": {"questions": ["...", "..."]}}
```

### POST `/api/v1/business-recommend/business`
业务推荐。

### POST `/api/v1/ecommerce-assistant/wechat/callback`
微信消息回调（主对话入口）。

### POST `/chat/v1/summary`
生成对话摘要。

### POST `/chat/v1/human-agent-summary`
生成人工坐席摘要。

---

## 6. 微信接入 `/api/v1/wechat`

### GET `/api/v1/wechat/callback`
微信服务器验证（echostr）。

### POST `/api/v1/wechat/callback`
接收微信公众号消息。

### POST `/api/v1/wechat/miniprogram/callback`
接收微信小程序消息。

---

## 7. 多平台接入 `/api/v1/platform`

### POST `/api/v1/platform/{platform}/callback`
通用平台回调（京东/淘宝/拼多多）。

### POST `/api/v1/platform/jd/sync/orders`
京东订单同步。`?tenant_id=default&days=1`

---

## 8. 健康检查 `/health`

### GET `/health`
全栈健康检查。

**响应：**
```json
{
  "status": "ok",
  "uptime_seconds": 1234.5,
  "checks": {
    "postgres": {"status": "ok", "latency_ms": 5},
    "chromadb": {"status": "ok", "circuit": {"healthy": true, "circuit_open": false, "consecutive_failures": 0}},
    "llm": {"status": "ok", "model": "deepseek-v4-flash"},
    "redis": {"status": "down"}
  }
}
```

- `status`: "ok" / "degraded" / "down"
- `chromadb.circuit.healthy`: 熔断器是否正常
- `chromadb.circuit.circuit_open`: 熔断是否打开（true=暂停 ChromaDB 操作）

---

## 9. 前端集成要点

### 响应解包示例（axios 拦截器）
```js
client.interceptors.response.use(resp => {
  const d = resp.data
  // 格式1: {code: 0, data: {...}}
  if (typeof d.code === 'number' && 'data' in d) {
    if (d.code !== 0) throw new Error(d.message)
    resp.data = d.data
  }
  // 格式2: {ret_code: "000000", data: {...}}
  else if (typeof d.ret_code === 'string' && 'data' in d) {
    if (d.ret_code !== '000000') throw new Error(d.ret_msg)
    resp.data = d.data
  }
  return resp
})
```

### 对话列表显示字段映射
```
conv.query          → 用户问题
conv.response       → AI 回复
conv.user_id        → 用户 ID
conv.created_at     → 时间
conv.quality_score  → 质量评分（0-1 float）
conv.user_approved  → 用户点赞（0/1）
```

### 画像展示建议
```
inferred_user_attribute.customer_type → 客户类型
inferred_user_attribute.role          → 用户角色
content_analysis.language             → 语种
content_analysis.sentiment            → 情绪
content_analysis.keywords             → 关键词列表
shopping_interaction.product_mentioned → 关注商品
session_metrics.total_turns           → 对话轮次
```
