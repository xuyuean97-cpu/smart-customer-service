"""
电商客服主图构建模块
"""
from langgraph.graph import StateGraph, START, END
from .state import EcommerceMainServiceState
from .main_nodes import (
    product_info,
    router,
    order_logistics,
    chitchat,
    translator,
    artificial,
    business,
    images_thinking,
    human
)
from langgraph.types import RetryPolicy


def build_ecommerce_service_graph():
    """
    构建电商客服系统图
    """
    # 1. 初始化图，使用新的状态类
    graph = StateGraph(EcommerceMainServiceState)

    # 2. 基础节点
    graph.add_node("translate_input_node", translator.translate_input, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("translate_output_node", translator.translate_output, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("emotion_node", artificial.detect_emotion, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("transfer_to_human", human.transfer_to_human, retry_policy=RetryPolicy(max_attempts=3))
    graph.add_node("images_thinking_node", images_thinking.images_thinking, retry_policy=RetryPolicy(max_attempts=3))

    # 3. 核心业务处理节点 (此处修复 AttributeError)
    graph.add_node("router", router.identify_intent, retry_policy=RetryPolicy(max_attempts=5))

    # --- 订单与物流模块 ---
    graph.add_node("order_logistics_search_node", order_logistics.order_logistics_search, retry_policy=RetryPolicy(max_attempts=5))
    graph.add_node("order_logistics_agent_node", order_logistics.order_logistics_agent, retry_policy=RetryPolicy(max_attempts=5))

    # --- 商品与政策模块 ---
    graph.add_node("product_info_search_node", product_info.product_info_search, retry_policy=RetryPolicy(max_attempts=5))
    graph.add_node("product_info_agent_node", product_info.product_info_agent, retry_policy=RetryPolicy(max_attempts=5))

    # --- 其他模块 ---
    graph.add_node("chitchat_node", chitchat.chitchat_agent, retry_policy=RetryPolicy(max_attempts=5))
    graph.add_node("business_assistant_node", business.business_agent, retry_policy=RetryPolicy(max_attempts=5))

    # 4. 连线逻辑 (Edges)
    graph.add_edge(START, "translate_input_node")
    graph.add_edge("translate_input_node", "emotion_node")

    graph.add_conditional_edges(
        "emotion_node",
        human.route_to_next,
        {
            "transfer_to_human": "transfer_to_human",
            "images_thinking_node": "images_thinking_node"
        }
    )

    graph.add_edge("images_thinking_node", "router")

    # 5. 路由逻辑 (需确保 router.route_to_next_node 返回的 key 与上面 add_node 匹配)
    graph.add_conditional_edges(
        "router",
        router.route_to_next_node,
        {
            "order_logistics_search_node": "order_logistics_search_node",
            "product_info_search_node": "product_info_search_node",
            "business_assistant_node": "business_assistant_node",
            "chitchat_node": "chitchat_node"                             # 补充闲聊路由
        }
    )

    # 业务流结束向
    graph.add_edge("order_logistics_search_node", "order_logistics_agent_node")
    graph.add_edge("product_info_search_node", "product_info_agent_node")

    graph.add_edge("order_logistics_agent_node", "translate_output_node")
    graph.add_edge("product_info_agent_node", "translate_output_node")
    graph.add_edge("chitchat_node", "translate_output_node")
    graph.add_edge("business_assistant_node", END)

    graph.add_edge("transfer_to_human", 'translate_output_node')
    graph.add_edge("translate_output_node", END)

    return graph

if __name__ == "__main__":
    graph = build_ecommerce_service_graph()
    graph_image = graph.compile().get_graph(xray=True).draw_mermaid_png()
    with open("main_graph1.png", "wb") as f:
        f.write(graph_image)
