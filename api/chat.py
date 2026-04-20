# import json
# import asyncio
# import time
# import os
# import base64
# from fastapi import APIRouter, WebSocket, WebSocketDisconnect
# from models.schemas import (
#     TextEventContent, RichContentEventContent, FormEventContent, FlightListEventContent, FlightInfo, EndEventContent, ErrorEventContent, ChatEvent
# )
# from agents.ecommerce_service import graph_manager
# from common.logging import get_logger

# # 使用专门的API聊天日志记录器
# logger = get_logger("api.chat")

# class EventGenerator:
#     """事件生成器，负责生成符合协议的事件流"""
    
#     def __init__(self):
#         self.sequence = 0
#         self.timestamp = int(time.time() * 1000)
    
#     def _next_sequence(self) -> int:
#         """获取下一个序号"""
#         self.sequence += 1
#         return self.sequence
    
#     def _generate_id(self, event_type: str, suffix: str = "") -> str:
#         """生成事件ID"""
#         timestamp = int(time.time() * 1000)
#         if suffix:
#             return f"{event_type}-{timestamp}-{suffix}"
#         return f"{event_type}-{timestamp}-{self._next_sequence()}"
    
#     def create_text_event(self, text: str, format_type: str = "plain") -> ChatEvent:
#         """创建文本事件"""
#         return ChatEvent(
#             id=self._generate_id("text"),
#             sequence=self._next_sequence(),
#             content=TextEventContent(text=text, format=format_type)
#         )
    
#     def create_rich_content_event(self, text: str, images: str = None, format_type: str = "plain", layout: str = "text_first") -> ChatEvent:
#         """创建富文本内容事件"""
#         from models.schemas import RichContentImage
        
#         # 处理图片数据 - images格式: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA/g||data:image/jpeg;base64,...'
#         image_objects = []
#         if images:
#             # 按||分割图片数据
#             image_parts = images.split('||')
#             img_count = 0
#             for image_part in image_parts:
#                 if image_part.strip():  # 确保不是空字符串
#                     # 检查是否是完整的data URI格式: data:image/png;base64,数据
#                     if image_part.startswith('data:') and ';base64,' in image_part:
#                         # 分离content_type和数据部分
#                         content_type_part, image_data = image_part.split(',', 1)
#                         # 提取content_type: data:image/png;base64 -> image/png
#                         content_type = content_type_part.replace('data:', '').replace(';base64', '')
                        
#                         img_count += 1
#                         image_obj = RichContentImage(
#                             id=f"img-{img_count}",
#                             content_type=content_type,
#                             data=image_part,  # 保持完整的data URI格式
#                             alt_text=f"图片{img_count}",
#                             description=f"相关图片内容"
#                         )
#                         image_objects.append(image_obj)
        
#         return ChatEvent(
#             id=self._generate_id("rich"),
#             sequence=self._next_sequence(),
#             content=RichContentEventContent(
#                 text=text,
#                 format=format_type,
#                 images=image_objects if image_objects else None,
#                 layout=layout
#             )
#         )
#     def create_form_event(
#         self,
#         form_id: str,
#         title: str,
#         action: str,
#         fields: list,
#         buttons: list,
#         description: str = None
#     ) -> ChatEvent:
#         """创建表单事件"""
#         from models.schemas import FormField, FormButton
        
#         fields_obj = [FormField(**field) for field in fields]
#         buttons_obj = [FormButton(**button) for button in buttons]
        
#         return ChatEvent(
#             id=self._generate_id("form", form_id.split('-')[0] if '-' in form_id else form_id),
#             sequence=self._next_sequence(),
#             content=FormEventContent(
#                 form_id=form_id,
#                 title=title,
#                 description=description,
#                 action=action,
#                 fields=fields_obj,
#                 buttons=buttons_obj
#             )
#         )
    
#     def create_end_event(self, suggestions: list = None, metadata: dict = None) -> ChatEvent:
#         """创建结束事件"""
#         return ChatEvent(
#             id=self._generate_id("end"),
#             sequence=self._next_sequence(),
#             content=EndEventContent(suggestions=suggestions, metadata=metadata)
#         )
    
#     def create_error_event(self, error_code: str, error_message: str) -> ChatEvent:
#         """创建错误事件"""
#         return ChatEvent(
#             id=self._generate_id("error", error_code),
#             sequence=self._next_sequence(),
#             content=ErrorEventContent(error_code=error_code, error_message=error_message)
#         )
    
#     def create_flight_list_event(
#         self,
#         title: str,
#         flights: list,
#         action_hint: str = None
#     ) -> ChatEvent:
#         """创建航班列表事件"""
#         flights_obj = [FlightInfo(**flight) for flight in flights]
        
#         return ChatEvent(
#             id=self._generate_id("flight_list"),
#             sequence=self._next_sequence(),
#             content=FlightListEventContent(
#                 title=title,
#                 flights=flights_obj,
#                 action_hint=action_hint
#             )
#         )

# # 新增电商聊天接口路由
# airport_router = APIRouter(prefix="/api/v1/airport-assistant", tags=["电商智能助手"])
# @airport_router.websocket("/chat/ws")
# async def airport_chat_websocket(websocket: WebSocket):
#     await websocket.accept()    
#     try:
#         while True:
#             try:
#                 message_data = await websocket.receive_json()
#             except json.JSONDecodeError as e:
#                 logger.error(f"❌ WebSocket JSON解析失败: {e}")
#                 error_response = {
#                     "event": "error",
#                     "data": {
#                         "id": f"error-json-{int(time.time() * 1000)}",
#                         "sequence": 1,
#                         "content": {
#                             "error_code": "invalid_json",
#                             "error_message": "请求格式错误，请发送有效的JSON数据"
#                         }
#                     }
#                 }
#                 await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
#                 continue
            
#             # 提取并验证必要字段
#             thread_id = message_data.get("thread_id")
#             user_id = message_data.get("user_id") 
#             query = message_data.get("query", "")
#             image_data = message_data.get("image", None)
#             metadata = message_data.get("metadata", {})
#             token = message_data.get("token", "")
#             Is_translate = metadata.get("Is_translate", False)
#             Is_emotion = metadata.get("Is_emotion", False)
            
#             # 提取技术环境信息字段
#             query_source = metadata.get("query_source","小程序")
#             query_device = metadata.get("query_device","手机")
#             query_ip = metadata.get("query_ip","")
#             network_type = metadata.get("network_type","5g")
            
#             # 构建技术环境metadata
#             technical_metadata = {}
#             technical_metadata["query_source"] = query_source
#             technical_metadata["query_device"] = query_device
#             technical_metadata["query_ip"] = query_ip
#             technical_metadata["network_type"] = network_type
            
#             # 检查是否提供了query或image中的至少一项
#             if not thread_id or not user_id or (not query and not image_data):
#                 logger.warning("❌ WebSocket 请求缺少必要字段")
#                 event_gen = EventGenerator()
#                 error_event = event_gen.create_error_event(
#                     error_code="missing_fields",
#                     error_message="必要字段缺失：thread_id, user_id, 以及query或image至少需要一项"
#                 )
#                 error_response = {
#                     "event": "error",
#                     "data": error_event.model_dump()
#                 }
#                 await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
#                 continue
#             event_gen = EventGenerator()
#             try:
#                 # 构建线程配置
#                 threads = {
#                     "configurable": {
#                         "user_id": user_id,
#                         "thread_id": thread_id,
#                         "user_query": query,
#                         # "image_url": image_url,  # 添加图片URL
#                         "image_data": image_data,
#                         "token": token,
#                         "Is_translate": Is_translate,
#                         "Is_emotion": Is_emotion,
#                         "metadata": technical_metadata
#                     }
#                 }
#                 if Is_translate:
#                     msg_nodes = ["translate_output_node"]
#                     custom_nodes = []
#                 else:
#                     # msg_nodes = ["airport_assistant_node", "flight_assistant_node", "chitchat_node", "business_assistant_node","transfer_to_human"]  
#                     # ================== 【修改开始】 ==================
#                     # 务必把所有电商业务相关的节点名都加进去！
#                     msg_nodes = [
#                         "chitchat_node",              # 闲聊
#                         "business_assistant_node",    # 业务办理
#                         "transfer_to_human",          # 转人工
#                         "order_logistics_node",       # <--- 新增：订单物流查询节点
#                         "order_logistics_agent", 
#                         "order_logistics",
#                         "product_info_search_node",   # <--- 新增：商品RAG检索节点
#                         "shopping_guide_node",        # <--- 新增：如果有导购节点的话
#                         # 保留旧节点名以防万一
#                         "airport_assistant_node", 
#                         "flight_assistant_node"
#                     ]         
#                     # custom_nodes = ["airport_info_search_node","flight_assistant_node","business_assistant_node"]
#                     # 如果商品检索返回富文本（图片），也要加到 custom_nodes
#                     custom_nodes = [
#                         "business_assistant_node", 
#                         "product_info_search_node",   # <--- 新增：为了处理富文本/ExpertQA格式
#                         "airport_info_search_node",
#                         "flight_assistant_node"
#                     ]
                
#                 # 发送开始事件（与原始接口保持一致）
#                 start_response = {
#                     "event": "start",
#                     "thread_id": thread_id,
#                     "user_id": user_id
#                 }
#                 await websocket.send_text(json.dumps(start_response, ensure_ascii=False))                
#                 # 处理聊天消息并发送事件
#                 result_count = 0
#                 async for msg_type, node, result in graph_manager.process_chat_message_stream(
#                     message=query,
#                     thread_id=threads,
#                     graph_id="ecommerce_service_graph",
#                     msg_nodes=msg_nodes,
#                     custom_nodes=custom_nodes
#                 ):
                    
#                     # ================== 【插入这行调试代码】 ==================
#                     logger.info(f"🕵️‍♂️ [抓捕现场] 收到节点消息 -> Node名: [{node}] | 类型: {msg_type} | 内容长度: {len(str(result))}")
#                     # ================== 【插入结束】 ==================
                    
#                     result_count += 1                    
#                     # 根据节点类型创建不同类型的事件
#                     if node=="business_assistant_node":
#                         # 业务节点 - 解析表单结构
#                         try:
#                             # 尝试解析JSON结构的表单数据
#                             form_data = json.loads(result)
#                             if form_data.get("type") == "form":
#                                 # 如果有服务说明，先发送文本事件
#                                 if form_data.get("info", {}).get("service_description"):
#                                     text_event = event_gen.create_text_event(
#                                         form_data["info"]["service_description"], "plain"
#                                     )
#                                     text_response = {
#                                         "event": "text",
#                                         "data": text_event.model_dump()
#                                     }
#                                     await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
#                                     await asyncio.sleep(0.01)
                                
#                                 # 生成表单事件
#                                 form_event = event_gen.create_form_event(
#                                     form_id=f"business-{int(time.time())}",
#                                     title=form_data.get("title", "业务办理"),
#                                     description=form_data.get("description", ""),
#                                     action=form_data.get("action", "/api/v1/forms/submit"),
#                                     fields=form_data.get("fields", []),
#                                     buttons=form_data.get("buttons", [])
#                                 )
                                
#                                 # 发送表单事件
#                                 form_response = {
#                                     "event": "form",
#                                     "data": form_event.model_dump()
#                                 }
#                                 await websocket.send_text(json.dumps(form_response, ensure_ascii=False))
#                                 logger.info("✅ WebSocket 发送了表单事件")
#                                 continue  # 跳过后面的文本事件发送
#                             else:
#                                 # 不是表单结构，按普通文本处理
#                                 text_event = event_gen.create_text_event(result)
#                         except json.JSONDecodeError:
#                             # JSON解析失败，按普通文本处理
#                             text_event = event_gen.create_text_event(result)
                    
#                     # 兼容电商的商品搜索节点
#                     elif msg_type=="custom" and (node=="airport_info_search_node" or node=="product_info_search_node"):
#                         # 处理电商知识 / 机场信息   
#                         try:
#                             flight_list_event = event_gen.create_flight_list_event(
#                                 title=result.get("title", "相关航班号信息"),
#                                 flights=result.get("data", []),
#                                 action_hint=result.get("action_hint")
#                             )
#                             flight_list_response = {
#                                 "event": "flight_list",
#                                 "data": flight_list_event.model_dump()
#                             }
#                             await websocket.send_text(json.dumps(flight_list_response, ensure_ascii=False))
#                             logger.info("✅ WebSocket 发送了航班列表事件")
#                             continue  # 跳过后面的文本事件发送

#                         except json.JSONDecodeError:
#                             # JSON解析失败，按普通文本处理
#                             text_event = event_gen.create_text_event(result)
#                     elif msg_type=="custom" and node=="airport_info_search_node":
#                         # 处理电商知识                        
#                         # 尝试解析 qa 事件的 JSON 数据
#                         try:
#                             if result.get('type') == 'expert_qa' and 'answer' in result:
#                                 logger.info(f"1111111result: {result}")
#                                 answer = result.get('answer', '')
#                                 images = result.get('images', '')
                               
#                                 # 如果有图片数据，创建富文本事件
#                                 if images:
#                                     rich_event = event_gen.create_rich_content_event(
#                                         text=answer,
#                                         images=images,
#                                         format_type="plain",
#                                         layout="text_first"
#                                     )
                                    
#                                     rich_response = {
#                                         "event": "rich_content",
#                                         "data": rich_event.model_dump()
#                                     }
#                                     await websocket.send_text(json.dumps(rich_response, ensure_ascii=False))
#                                     logger.info("✅ WebSocket 发送了富文本内容事件")
#                                     continue  # 跳过后面的文本事件发送
#                                 else:
#                                     # 只有文本，创建普通文本事件
#                                     text_event = event_gen.create_text_event(answer)
#                             else:
#                                 # 不是qa结构或缺少answer，按普通文本处理
#                                 text_event = event_gen.create_text_event(result)
#                         except json.JSONDecodeError:
#                             # JSON解析失败，按普通文本处理
#                             text_event = event_gen.create_text_event(result)
#                     elif node=="transfer_to_human":
#                         text_event = event_gen.create_text_event(result)
#                         text_response = {
#                             "event": "transfer_to_human",
#                             "data": text_event.model_dump()
#                         }
#                         await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
#                         logger.info("✅ WebSocket 发送了转人工事件")
#                         continue
#                     else:
#                         # 其他节点 - 默认文本事件
#                         text_event = event_gen.create_text_event(result)
                    
#                     # 发送文本事件
#                     text_response = {
#                         "event": "text",
#                         "data": text_event.model_dump()
#                     }
#                     await websocket.send_text(json.dumps(text_response, ensure_ascii=False))
#                     # await asyncio.sleep(0.01)  # 控制流式输出速度
                                 
#                 # 发送结束事件
#                 end_event = event_gen.create_end_event(
#                     suggestions=["查询行李规定", "值机办理", "航班动态"],
#                     metadata={"processing_time": "1.2s", "results_count": result_count}
#                 )
#                 end_response = {
#                     "event": "end",
#                     "data": end_event.model_dump()
#                 }
#                 await websocket.send_text(json.dumps(end_response, ensure_ascii=False))
#                 logger.info("✅ WebSocket 发送了结束事件")
                
#             except Exception as e:
#                 logger.error(f"电商 WebSocket 聊天处理异常: {str(e)}", exc_info=True)
                
#                 # 发送错误事件
#                 error_event = event_gen.create_error_event(
#                     error_code="service_unavailable",
#                     error_message="服务暂时不可用，请稍后再试"
#                 )
#                 error_response = {
#                     "event": "error",
#                     "data": error_event.model_dump()
#                 }
#                 await websocket.send_text(json.dumps(error_response, ensure_ascii=False))
                
#     except WebSocketDisconnect:
#         logger.info("电商智能客服 WebSocket 连接已断开")
#     except Exception as e:
#         logger.error(f"电商智能客服 WebSocket 连接异常: {str(e)}", exc_info=True)
#         try:
#             await websocket.close()
#         except:
#             pass 
import json
import asyncio
import time
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models.schemas import (
    TextEventContent, RichContentEventContent, FormEventContent, FlightListEventContent, FlightInfo, EndEventContent, ErrorEventContent, ChatEvent
)
from agents.ecommerce_service import graph_manager
from common.logging import get_logger

# 使用专门的API聊天日志记录器
logger = get_logger("api.chat")

class EventGenerator:
    """事件生成器"""
    def __init__(self):
        self.sequence = 0
        self.timestamp = int(time.time() * 1000)
    
    def _next_sequence(self) -> int:
        self.sequence += 1
        return self.sequence
    
    def _generate_id(self, event_type: str, suffix: str = "") -> str:
        timestamp = int(time.time() * 1000)
        suffix_part = f"-{suffix}" if suffix else ""
        return f"{event_type}-{timestamp}-{self._next_sequence()}{suffix_part}"
    
    def create_text_event(self, text: str, format_type: str = "plain") -> ChatEvent:
        return ChatEvent(id=self._generate_id("text"), sequence=self._next_sequence(), content=TextEventContent(text=text, format=format_type))

    def create_rich_content_event(self, text: str, images: str = None, format_type: str = "plain", layout: str = "text_first") -> ChatEvent:
        from models.schemas import RichContentImage
        image_objects = []
        if images:
            image_parts = images.split('||')
            img_count = 0
            for image_part in image_parts:
                if image_part.strip() and image_part.startswith('data:') and ';base64,' in image_part:
                    content_type_part, image_data = image_part.split(',', 1)
                    content_type = content_type_part.replace('data:', '').replace(';base64', '')
                    img_count += 1
                    image_obj = RichContentImage(
                        id=f"img-{img_count}", content_type=content_type, data=image_part, alt_text=f"图片{img_count}", description=f"相关图片内容"
                    )
                    image_objects.append(image_obj)
        return ChatEvent(id=self._generate_id("rich"), sequence=self._next_sequence(), content=RichContentEventContent(text=text, format=format_type, images=image_objects if image_objects else None, layout=layout))

    def create_form_event(self, form_id: str, title: str, action: str, fields: list, buttons: list, description: str = None) -> ChatEvent:
        from models.schemas import FormField, FormButton
        fields_obj = [FormField(**field) for field in fields]
        buttons_obj = [FormButton(**button) for button in buttons]
        # 确保 form_id 是简单的字符串
        safe_form_id = str(form_id).split('-')[0] if '-' in str(form_id) else str(form_id)
        return ChatEvent(id=self._generate_id("form", safe_form_id), sequence=self._next_sequence(), content=FormEventContent(form_id=str(form_id), title=title, description=description, action=action, fields=fields_obj, buttons=buttons_obj))
    
    def create_end_event(self, suggestions: list = None, metadata: dict = None) -> ChatEvent:
        return ChatEvent(id=self._generate_id("end"), sequence=self._next_sequence(), content=EndEventContent(suggestions=suggestions, metadata=metadata))
    
    def create_error_event(self, error_code: str, error_message: str) -> ChatEvent:
        return ChatEvent(id=self._generate_id("error", error_code), sequence=self._next_sequence(), content=ErrorEventContent(error_code=error_code, error_message=error_message))
    
    def create_flight_list_event(self, title: str, flights: list, action_hint: str = None) -> ChatEvent:
        flights_obj = [FlightInfo(**flight) for flight in flights]
        return ChatEvent(id=self._generate_id("flight_list"), sequence=self._next_sequence(), content=FlightListEventContent(title=title, flights=flights_obj, action_hint=action_hint))


# 新增电商聊天接口路由
airport_router = APIRouter(prefix="/api/v1/ecommerce-assistant", tags=["电商智能助手"])

@airport_router.websocket("/chat/ws")
async def airport_chat_websocket(websocket: WebSocket):
    await websocket.accept()    
    try:
        while True:
            # 1. 接收消息
            try:
                message_data = await websocket.receive_json()
            except json.JSONDecodeError as e:
                logger.error(f"❌ WebSocket JSON解析失败: {e}")
                continue
            
            # 2. 提取字段
            thread_id = message_data.get("thread_id")
            user_id = message_data.get("user_id") 
            query = message_data.get("query", "")
            image_data = message_data.get("image", None)
            metadata = message_data.get("metadata", {})
            token = message_data.get("token", "")
            Is_translate = metadata.get("Is_translate", False)
            Is_emotion = metadata.get("Is_emotion", False)
            if not thread_id or not user_id:
                logger.warning("❌ 缺少 thread_id 或 user_id")
                continue

            event_gen = EventGenerator()
            
            # 3. 构建配置
            threads = {
                "configurable": {
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "user_query": query,
                    "image_data": image_data,
                    "token": token,
                    "Is_translate": Is_translate,
                    "Is_emotion": Is_emotion,
                    "metadata": metadata
                },
            }
            graph_inputs = {
                "question": query,        # 对应 State 中的 question 字段
                "user_id": user_id,       # 【关键】必须放在这里，Text2SQL 节点才能从 state["user_id"] 拿到
                "image_data": image_data, # 如果你的 State 定义了图片字段
                # 如果有 metadata 也建议放进来，方便后续节点使用
                "metadata": metadata,  
            }
            # 这些数据用于 LangGraph 的线程隔离、记忆加载等
            graph_config = {
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": user_id,     # 这里放一份用于 checkpoint 隔离（可选）
                    "Is_translate": Is_translate,
                    "Is_emotion": Is_emotion
                }
            }
            # 4. 发送开始事件
            await websocket.send_text(json.dumps({
                "event": "start",
                "thread_id": thread_id,
                "user_id": user_id
            }, ensure_ascii=False))

            result_count = 0
            
            try:
                # ------------------------------------------------------------
                # 逻辑优化版 Graph 执行
                # ------------------------------------------------------------
                
                # 防范性检查
                # if "ecommerce_service_graph" not in graph_manager._registered_graphs:
                #     logger.error("❌ 未找到 ecommerce_service_graph，无法执行！")
                #     continue

                # 2. 编译图 (Handle Compiled vs Not Compiled)
                async with graph_manager.get_compiled_graph("ecommerce_service_graph") as app:
                    
                    logger.info(f"🚀 开始执行 Graph (Redis 记忆版已启动)...")
                    
                    # 定义不想展示给用户的内部节点 (黑名单)
                    INTERNAL_NODES = [
                        "router", 
                        "translate_input_node", 
                        "emotion_node", 
                        "images_thinking_node", 
                        "translate_output_node"
                    ]

                # 3. 执行流式输出
                    async for event in app.astream(input = graph_inputs, config=threads, stream_mode="updates"):
                        for node_name, node_output in event.items():
                            result_count += 1
                            
                            # [规则 1] 跳过内部逻辑节点
                            if node_name in INTERNAL_NODES:
                                logger.debug(f"🔇 忽略内部节点输出: {node_name}")
                                continue
                                
                            logger.info(f"👉 处理节点输出: {node_name} | 类型: {type(node_output)}")
                            
                            # [规则 2] 智能内容提取
                            content_to_send = None
                            is_rich_content = False
                            
                            # 情况 A: 包含 messages 列表 (标准的 Agent State 更新)
                            # 例如: {'messages': [AIMessage(content='您好...')]}
                            if isinstance(node_output, dict) and "messages" in node_output:
                                messages = node_output["messages"]
                                if isinstance(messages, list) and len(messages) > 0:
                                    last_msg = messages[-1]
                                    # 确保只发送 AI 的回复，不发送用户的提问或 System Prompt
                                    # 判断依据：content 存在，且通常 type='ai' 或 role='assistant'
                                    # 如果是 LangChain 对象，它有 type 属性；如果是 dict，看 role
                                    is_ai_msg = False
                                    if hasattr(last_msg, 'type') and last_msg.type == 'ai':
                                        is_ai_msg = True
                                    elif isinstance(last_msg, dict) and last_msg.get('role') == 'assistant':
                                        is_ai_msg = True
                                    # 兜底：如果就是一条单一的 AIMessage 对象，也算
                                    elif not isinstance(last_msg, dict) and hasattr(last_msg, 'content'):
                                        is_ai_msg = True

                                    if is_ai_msg:
                                        if hasattr(last_msg, 'content'):
                                            content_to_send = str(last_msg.content)
                                        elif isinstance(last_msg, dict):
                                            content_to_send = last_msg.get('content')

                            # 情况 B: 包含 answer 字段 (RAG / ExpertQA 常用格式)
                            # 例如: {'answer': '...', 'images': '...'}
                            elif isinstance(node_output, dict) and "answer" in node_output:
                                content_to_send = node_output["answer"]
                                # 检查是否有图片，升级为富文本
                                if node_output.get("images"):
                                    logger.info(f"🖼️ 发现图文内容: {node_name}")
                                    rich_event = event_gen.create_rich_content_event(
                                        text=content_to_send,
                                        images=node_output.get("images"),
                                        layout="text_first"
                                    )
                                    await websocket.send_text(json.dumps({
                                        "event": "rich_content",
                                        "data": rich_event.model_dump()
                                    }, ensure_ascii=False))
                                    is_rich_content = True
                            
                            # 情况 C: 表单特殊处理
                            # 有些节点直接返回包含 type: form 的字典或 JSON 字符串
                            elif isinstance(node_output, (dict, str)):
                                try:
                                    data_check = node_output if isinstance(node_output, dict) else json.loads(node_output)
                                    if isinstance(data_check, dict) and data_check.get("type") == "form":
                                        logger.info(f"📝 发现表单: {node_name}")
                                        form_event = event_gen.create_form_event(
                                            form_id=f"biz-{int(time.time())}",
                                            title=data_check.get("title", "业务办理"),
                                            action=data_check.get("action", ""),
                                            fields=data_check.get("fields", []),
                                            buttons=data_check.get("buttons", [])
                                        )
                                        await websocket.send_text(json.dumps({"event": "form", "data": form_event.model_dump()}, ensure_ascii=False))
                                        # 表单发送后，通常不需要再发文本，直接 continue
                                        continue 
                                except:
                                    pass # 解析失败，不是表单，继续后续逻辑

                            # [规则 3] 内容发送与安全清洗
                            if content_to_send and not is_rich_content:
                                # 强制转字符串
                                final_text = str(content_to_send)
                                
                                # 🛡️ 安全防御：防止发送原始的 State 字典字符串
                                # 如果文本看起来像 Python 字典 "{'user_query': ...}"，坚决拦截
                                if final_text.strip().startswith("{") and "'user_query':" in final_text:
                                    logger.warning(f"🛡️ 拦截到原始 State 数据泄露: {node_name}")
                                    continue
                                    
                                if final_text.strip():
                                    logger.info(f"✅ 发送文本: {node_name}")
                                    text_event = event_gen.create_text_event(final_text)
                                    await websocket.send_text(json.dumps({
                                        "event": "text",
                                        "data": text_event.model_dump()
                                    }, ensure_ascii=False))

            except Exception as e:
                logger.error(f"Graph执行异常: {e}", exc_info=True)
                err_event = event_gen.create_error_event("runtime_error", str(e))
                await websocket.send_text(json.dumps({"event": "error", "data": err_event.model_dump()}, ensure_ascii=False))

            # 5. 发送结束事件
            end_event = event_gen.create_end_event(suggestions=["查询物流", "售后政策"], metadata={"count": result_count})
            await websocket.send_text(json.dumps({"event": "end", "data": end_event.model_dump()}, ensure_ascii=False))
            logger.info("✅ 结束事件已发送")

    except WebSocketDisconnect:
        logger.info("WebSocket 断开")
    except Exception as e:
        logger.error(f"WebSocket 全局异常: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass
from fastapi import Request
import json
import base64
import struct
import random
import string
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from fastapi.responses import PlainTextResponse, JSONResponse
# ==========================================
# 🔑 请务必填入你自己的 APPID 和 EncodingAESKey！
# ==========================================
WECHAT_APPID = "YXQ1xwN7tLu6u6j"
WECHAT_AES_KEY = "N8ddFblMmZdMi3k1SHuGeccjmev2KrjeWJKkUs4ACPB"

def decrypt_wechat_msg(encrypted_text: str, aes_key_str: str) -> dict:
    try:
        aes_key = base64.b64decode(aes_key_str + "=")
        iv = aes_key[:16]
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(base64.b64decode(encrypted_text)) + decryptor.finalize()
        
        pad_len = decrypted[-1]
        decrypted = decrypted[:-pad_len]
        content = decrypted[16:]
        msg_len = struct.unpack("!I", content[:4])[0]
        msg_str = content[4:4+msg_len].decode("utf-8").strip()
        
        # 兼容 XML 和 JSON 两种格式
        if msg_str.startswith("<xml>"):
            import xml.etree.ElementTree as ET
            xml_tree = ET.fromstring(msg_str)
            user_id = xml_tree.findtext('userid', 'unknown_user')
            content_node = xml_tree.find('content')
            query = content_node.findtext('msg', '') if content_node is not None else xml_tree.findtext('msg', '')
            return {"query": query, "from_user_name": user_id}
        else:
            return json.loads(msg_str)
    except Exception as e:
        logger.error(f"❌ 解密失败: {e}")
        return {}

def encrypt_wechat_reply(reply_dict: dict, aes_key_str: str, appid: str) -> str:
    msg_str = json.dumps(reply_dict, ensure_ascii=False).encode('utf-8')
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=16)).encode('utf-8')
    msg_len = struct.pack("!I", len(msg_str))
    
    unencrypted_bytes = random_str + msg_len + msg_str + appid.encode('utf-8')
    block_size = 32
    pad_len = block_size - (len(unencrypted_bytes) % block_size)
    pad_len = pad_len if pad_len != 0 else block_size
    padding = bytes([pad_len] * pad_len)
    
    aes_key = base64.b64decode(aes_key_str + "=")
    iv = aes_key[:16]
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_bytes = encryptor.update(unencrypted_bytes + padding) + encryptor.finalize()
    
    return base64.b64encode(encrypted_bytes).decode('utf-8')


@airport_router.post("/wechat/callback", summary="微信 POST 消息接口")
async def wechat_bot_callback(request: Request):
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode('utf-8').strip()
        
        # 1. 提取并兼容明文/密文消息
        real_payload = {}
        encrypted_data = None
        
        if body_str.startswith("{"):
            payload = json.loads(body_str)
            # 如果有关闭加密，直接拿到的就是原始数据；如果开启了加密，才会有 encrypted
            encrypted_data = payload.get("encrypted") or payload.get("encrypt")
            if encrypted_data:
                real_payload = decrypt_wechat_msg(encrypted_data, WECHAT_AES_KEY)
            else:
                # 💡 修复点 1：如果是明文，直接把 payload 当作真实数据
                real_payload = payload
        else:
            encrypted_data = body_str
            real_payload = decrypt_wechat_msg(encrypted_data, WECHAT_AES_KEY)

        # 💡 修复点 2：第三方接口传来的字段名首字母是大写的！(Query, UserId)
        query = real_payload.get("Query") or real_payload.get("query", "")
        user_id = real_payload.get("UserId") or real_payload.get("from_user_name", "unknown_user")
        
        if not query:
            # 即使没收到问题，也要按微信标准格式返回，不能再返回 {"status": "0"} 了
            return JSONResponse(content={
                "answer_type": "text",
                "text_info": {"short_answer": "收到空消息"}
            })

        logger.info(f"💬 大模型开始接管 | 用户: {user_id} | 内容: {query}")

        # 2. 执行 LangGraph (这部分完全保留你原来的逻辑)
        final_answer = ""
        thread_id = f"wechat-{user_id}" 
        threads = {"configurable": {"user_id": user_id, "thread_id": thread_id, "user_query": query, "Is_translate": False, "Is_emotion": False}}
        graph_inputs = {"question": query, "user_id": user_id, "metadata": {"source": "wechat"}}

        async with graph_manager.get_compiled_graph("ecommerce_service_graph") as app:
            INTERNAL_NODES =["router", "translate_input_node", "emotion_node", "images_thinking_node", "translate_output_node"]
            async for event in app.astream(input=graph_inputs, config=threads, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_name in INTERNAL_NODES: continue
                    if isinstance(node_output, dict) and "messages" in node_output:
                        messages = node_output["messages"]
                        if messages and (hasattr(messages[-1], 'type') and messages[-1].type == 'ai'):
                            final_answer = str(getattr(messages[-1], 'content', ''))
                    elif isinstance(node_output, dict) and "answer" in node_output:
                        final_answer = str(node_output["answer"])

        if not final_answer.strip():
            final_answer = "抱歉，我还不知道怎么回答这个问题。"
            
        logger.info(f"✅ 大模型思考完毕 | 准备同步返回: {final_answer[:20]}...")
        
        # 3. 💡 修复点 3：必须严格按照微信官方文档的 Schema 构造回复
        reply_dict = {
            "answer_type": "text",
            "text_info": {
                "short_answer": final_answer
            }
        }
        
        # 4. 根据是否加密，决定返回类型
        if encrypted_data:
            # 注意：按照官方文档，加密必须将 json 字符串 AES 后 base64，并作为纯文本返回
            encrypted_reply = encrypt_wechat_reply(json.dumps(reply_dict, ensure_ascii=False), WECHAT_AES_KEY, WECHAT_APPID)
            return PlainTextResponse(content=encrypted_reply)
        else:
            # 没有加密，直接返回标准的 JSON
            return JSONResponse(content=reply_dict)

    except Exception as e:
        logger.error(f"❌ 接口发生错误: {e}", exc_info=True)
        # 即使报错，也必须老老实实回标准 JSON
        return JSONResponse(content={
            "answer_type": "text",
            "text_info": {"short_answer": "系统开小差了，请稍后再试。"}
        })