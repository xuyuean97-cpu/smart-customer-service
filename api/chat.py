import json
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from models.schemas import (
    TextEventContent, RichContentEventContent, FormEventContent, OrderListEventContent, OrderInfo, EndEventContent, ErrorEventContent, ChatEvent
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
                        id=f"img-{img_count}", content_type=content_type, data=image_part, alt_text=f"图片{img_count}", description="相关图片内容"
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

    def create_order_list_event(self, title: str, orders: list, action_hint: str = None) -> ChatEvent:
        orders_obj = [OrderInfo(**order) for order in orders]
        return ChatEvent(id=self._generate_id("order_list"), sequence=self._next_sequence(), content=OrderListEventContent(title=title, orders=orders_obj, action_hint=action_hint))


# 新增电商聊天接口路由
ecommerce_router = APIRouter(prefix="/api/v1/ecommerce-assistant", tags=["电商智能助手"])

@ecommerce_router.websocket("/chat/ws")
async def ecommerce_chat_websocket(websocket: WebSocket):
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
            tenant_id = message_data.get("tenant_id", "default")
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
                    "tenant_id": tenant_id,
                    "user_query": query,
                    "image_data": image_data,
                    "token": token,
                    "Is_translate": Is_translate,
                    "Is_emotion": Is_emotion,
                    "metadata": metadata
                },
            }
            graph_inputs = {
                "question": query,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "image_data": image_data,
                "metadata": metadata,
            }
            # LangGraph 线程隔离 + 记忆加载
            # 4. 发送开始事件 + 即时 ACK（用户感知 <500ms）
            await websocket.send_text(json.dumps({
                "event": "start",
                "thread_id": thread_id,
                "user_id": user_id
            }, ensure_ascii=False))
            await websocket.send_text(json.dumps({
                "event": "thinking",
                "text": "亲，收到您的问题了，小二正在为您查询中～"
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

                    logger.info("🚀 开始执行 Graph (Redis 记忆版已启动)...")

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
                                except Exception:
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
        except Exception:
            pass


# ── 流式 HTTP (SSE) 端点 ──

from pydantic import BaseModel, Field  # noqa: E402


class ChatStreamRequest(BaseModel):
    thread_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    tenant_id: str = Field(default="default")
    query: str = Field(default="", description="用户问题")
    image: dict | None = Field(default=None, description="图片数据 {filename, content_type, data}")
    metadata: dict = Field(default_factory=dict)


async def _run_graph_stream(graph_inputs: dict, threads: dict):
    """共享的 LangGraph 流式执行器，产出 SSE 事件字符串"""
    event_gen = EventGenerator()
    result_count = 0
    INTERNAL_NODES = ["router", "translate_input_node", "emotion_node", "images_thinking_node", "translate_output_node"]

    # 1. 发送开始事件
    yield f'data: {json.dumps({"event":"start","thread_id":threads["configurable"]["thread_id"],"user_id":threads["configurable"]["user_id"]}, ensure_ascii=False)}\n\n'
    # 2. 即时 ACK — 第三方平台通常 3-5s 超时，这里 100ms 内返回
    yield f'data: {json.dumps({"event":"thinking","text":"亲，收到您的问题了，小二正在为您查询中～"}, ensure_ascii=False)}\n\n'

    try:
        async with graph_manager.get_compiled_graph("ecommerce_service_graph") as app:
            async for event in app.astream(input=graph_inputs, config=threads, stream_mode="updates"):
                for node_name, node_output in event.items():
                    result_count += 1

                    if node_name in INTERNAL_NODES:
                        continue

                    content_to_send = None

                    if isinstance(node_output, dict) and "messages" in node_output:
                        messages = node_output["messages"]
                        if isinstance(messages, list) and len(messages) > 0:
                            last_msg = messages[-1]
                            if hasattr(last_msg, 'content'):
                                content_to_send = str(last_msg.content)
                            elif isinstance(last_msg, dict):
                                content_to_send = last_msg.get('content')
                    elif isinstance(node_output, dict) and "data" in node_output:
                        data = node_output["data"]
                        if isinstance(data, str):
                            content_to_send = data
                        elif isinstance(data, dict):
                            content_to_send = json.dumps(data, ensure_ascii=False)

                    if content_to_send:
                        yield f'data: {json.dumps({"event":"text","text":str(content_to_send)}, ensure_ascii=False)}\n\n'

    except Exception as e:
        logger.error(f"Graph 执行异常: {e}", exc_info=True)
        yield f'data: {json.dumps({"event":"error","error":str(e)}, ensure_ascii=False)}\n\n'

    # 结束事件
    end_event = event_gen.create_end_event(suggestions=[], metadata={"count": result_count})
    yield f'data: {json.dumps({"event":"end","data":end_event.model_dump()}, ensure_ascii=False)}\n\n'


@ecommerce_router.post("/chat/stream")
async def ecommerce_chat_stream(body: ChatStreamRequest):
    """
    流式 HTTP 聊天 (Server-Sent Events)

    curl 示例:
      curl -X POST http://localhost:8081/api/v1/ecommerce-assistant/chat/stream \
        -H 'Content-Type: application/json' \
        -d '{"thread_id":"t1","user_id":"u1","query":"你们有什么显示器？"}' \
        --no-buffer

    前端 fetch 示例:
      const resp = await fetch('/api/v1/ecommerce-assistant/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({thread_id:'t1', user_id:'u1', query:'你好'})
      })
      const reader = resp.body.getReader()
      // 逐行解析 SSE 格式
    """
    threads = {
        "configurable": {
            "user_id": body.user_id,
            "thread_id": body.thread_id,
            "tenant_id": body.tenant_id,
            "user_query": body.query,
            "image_data": body.image,
            "metadata": body.metadata,
        },
    }
    graph_inputs = {
        "question": body.query,
        "user_id": body.user_id,
        "tenant_id": body.tenant_id,
        "image_data": body.image,
        "metadata": body.metadata,
    }

    return StreamingResponse(
        _run_graph_stream(graph_inputs, threads),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


import base64  # noqa: E402
import struct  # noqa: E402
import random  # noqa: E402
import string  # noqa: E402
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: E402
from cryptography.hazmat.backends import default_backend  # noqa: E402
from fastapi.responses import PlainTextResponse, JSONResponse  # noqa: E402
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


@ecommerce_router.post("/wechat/callback", summary="微信 POST 消息接口")
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
                    if node_name in INTERNAL_NODES:
                        continue
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
