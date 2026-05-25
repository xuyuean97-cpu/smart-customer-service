# 智能客服系统 - 文档中心

欢迎来到智能客服系统的文档中心！这里提供了完整的系统介绍、技术文档和API参考。

## 📚 文档结构

### 核心功能页面

- **[首页](index.html)** - 系统概览和快速入门
- **[核心优势](features.html)** - 六大核心功能详细介绍
- **[评估体系](evaluation.html)** - 基于DeepEval的全方位评估框架
- **[专家审核](expert-review.html)** - 专家审核机制与系统自进化
- **[在线体验](chat.html)** - 🔥 实时对话体验（WebSocket驱动）

### 技术文档

- **[用户画像](user-profile.html)** - 三步走用户画像系统
- **[智能记忆](memory-filter.html)** - 基于多因子评分的记忆筛选算法
- **[专家审核演示](expert_review_v2.html)** - 完整的审核系统界面

## 🎯 核心特性

### 1. 对话能力 💬
- **追问/反问机制** - 行业唯一支持
- **决策-执行分离架构** - 避免巨石型Prompt
- **多智能体协作** - 基于LangGraph

### 2. 评估能力 🧪
- **DeepEval驱动** - 40+ 研究支持的评估指标
- **端到端评估** - 组件级到系统级全覆盖
- **实时监控** - 可视化评估看板

### 3. 进化能力 🔄
- **专家审核平台** - 智能筛选、批量操作、质量评分
- **四维自进化闭环**：
  1. 动态知识库增强
  2. 向量模型微调
  3. 垂直大模型训练
  4. Prompt持续优化

## 🚀 快速开始

1. **浏览核心功能**：从[首页](index.html)开始了解系统概览
2. **了解评估体系**：访问[评估体系](evaluation.html)了解DeepEval评估框架
3. **查看专家审核**：参考[专家审核](expert-review.html)了解系统自进化机制

## 📖 文档导航

所有页面都包含统一的导航栏，方便快速访问：

```
首页 > 核心优势 > 评估体系 > 专家审核 > 在线体验
```

技术文档：

```
用户画像 > 智能记忆 > 专家审核演示
```

## 🔗 相关链接

- **GitHub仓库**：[smart-customer-service-system](https://github.com/traveler-leon/smart-customer-service-system)
- **DeepEval**：[https://deepeval.com/](https://deepeval.com/)
- **LangChain**：[https://www.langchain.com/](https://www.langchain.com/)
- **LangGraph**：[https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)

## 💡 特别说明

- 所有页面均采用响应式设计，支持移动端访问
- 技术文档包含完整的代码示例和API调用说明
- 系统完全开源，基于MIT License

### 🆕 在线体验功能

**[chat.html](chat.html)** 提供了完整的WebSocket实时对话体验：

- ✅ **实时通信** - 基于WebSocket的流式对话
- 🎨 **现代UI** - 渐变背景、玻璃态效果、流畅动画
- 📸 **图片支持** - 可上传图片进行多模态对话
- 🎯 **事件类型** - 支持文本、富文本、订单列表、表单、转人工等多种事件
- 💬 **智能推荐** - 对话结束后提供问题推荐
- 🔄 **自动重连** - 连接断开自动重连机制
- 📱 **响应式** - 完美适配移动端和桌面端

**支持的事件类型：**
- `text` - 普通文本消息
- `rich_content` - 富文本内容（文本+图片）
- `flight_list` - 订单信息列表
- `form` - 交互式表单
- `transfer_to_human` - 转人工客服
- `error` - 错误提示

---

**最后更新**：2024年

**许可证**：MIT License

**联系方式**：[GitHub Issues](https://github.com/traveler-leon/smart-customer-service-system/issues)
