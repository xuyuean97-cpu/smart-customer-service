"""
微信消息通道 — 公众号 / 小程序消息解析
"""
import hashlib
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any

from . import MessageChannel, ChannelMessage
from common.logging import get_logger

logger = get_logger("agents.channels.wechat")


class WeChatOfficialAccountChannel(MessageChannel):
    """
    微信公众号消息通道

    消息格式:
        <xml>
            <ToUserName><![CDATA[gh_xxx]]></ToUserName>
            <FromUserName><![CDATA[oUserOpenID]]></FromUserName>
            <CreateTime>1234567890</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[用户消息内容]]></Content>
            <MsgId>1234567890</MsgId>
        </xml>
    """

    def __init__(self, token: str = "", app_id: str = "", app_secret: str = ""):
        self.token = token
        self.app_id = app_id
        self.app_secret = app_secret

    async def parse_message(self, raw_data: bytes) -> ChannelMessage:
        """解析微信 XML 消息 → ChannelMessage"""
        try:
            root = ET.fromstring(raw_data)
            msg_type = self._get_text(root, "MsgType")
            from_user = self._get_text(root, "FromUserName")  # OpenID
            to_user = self._get_text(root, "ToUserName")
            create_time = self._get_text(root, "CreateTime")

            # 提取消息内容
            content = ""
            image_url = None

            if msg_type == "text":
                content = self._get_text(root, "Content")
            elif msg_type == "image":
                image_url = self._get_text(root, "PicUrl")
                content = "[图片消息]"
                # 通过 MediaId 可下载图片
                media_id = self._get_text(root, "MediaId")
                if media_id:
                    image_url = f"wechat_media://{media_id}"
            elif msg_type == "voice":
                content = "[语音消息]"
            elif msg_type == "event":
                event = self._get_text(root, "Event")
                if event == "subscribe":
                    content = "关注公众号"
                elif event == "unsubscribe":
                    content = "取消关注"
                elif event == "CLICK":
                    content = f"点击菜单: {self._get_text(root, 'EventKey')}"
                else:
                    content = f"事件: {event}"

            # 映射 OpenID → 内部 user_id
            user_id = await self._resolve_user_id(from_user)

            return ChannelMessage(
                query=content,
                user_id=user_id,
                tenant_id="default",
                channel="wechat_oa",
                image_url=image_url,
                metadata={
                    "msg_type": msg_type,
                    "openid": from_user,
                    "create_time": create_time,
                    "to_user": to_user,
                },
            )

        except ET.ParseError as e:
            logger.error(f"微信 XML 解析失败: {e}")
            return ChannelMessage(
                query="[消息解析失败]",
                user_id="unknown",
                channel="wechat_oa",
                metadata={"error": str(e)},
            )

    async def verify_signature(
        self, signature: str, timestamp: str, nonce: str, echostr: str = ""
    ) -> bool:
        """验证微信服务器签名"""
        if not self.token:
            logger.warning("微信 Token 未配置，跳过签名验证")
            return True  # 测试环境跳过

        tmp_list = sorted([self.token, timestamp, nonce])
        tmp_str = "".join(tmp_list)
        calculated = hashlib.sha1(tmp_str.encode()).hexdigest()

        if calculated != signature:
            logger.warning(f"微信签名验证失败: expected={calculated}, got={signature}")
            return False
        return True

    async def build_reply(
        self, response_text: str, original_msg: ChannelMessage
    ) -> str:
        """构建微信 XML 回复"""
        from_user = original_msg.metadata.get("openid", "unknown")
        to_user = original_msg.metadata.get("to_user", "gh_default")
        timestamp = int(time.time())

        # 转义 XML 特殊字符
        safe_text = (
            response_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

        return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{safe_text}]]></Content>
</xml>"""

    async def _resolve_user_id(self, openid: str) -> str:
        """
        微信 OpenID → 内部 user_id 映射。
        优先查数据库，不存在则创建新用户。
        """
        try:
            from auth.database import SessionLocal
            from auth.models import User

            db = SessionLocal()
            try:
                user = db.query(User).filter(User.wechat_openid == openid).first()
                if user:
                    return user.id
                # 新用户：自动注册
                import uuid
                new_id = str(uuid.uuid4())
                db.add(User(
                    id=new_id,
                    phone=f"wechat_{openid[:16]}",
                    nickname=f"微信用户{openid[-6:]}",
                    wechat_openid=openid,
                    tenant_id="default",
                ))
                db.commit()
                logger.info(f"微信新用户注册: openid={openid[:10]}..., id={new_id}")
                return new_id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"微信用户映射失败: {e}")
            return openid  # 降级：直接使用 OpenID 作为 user_id

    @staticmethod
    def _get_text(element, tag: str) -> str:
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""


class WeChatMiniProgramChannel(MessageChannel):
    """
    微信小程序消息通道

    消息格式: JSON
        {
            "FromUserName": "oUserOpenID",
            "Content": "用户消息",
            "MsgType": "text",
            ...
        }
    """

    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret

    async def parse_message(self, raw_data: Dict[str, Any]) -> ChannelMessage:
        """解析小程序 JSON 消息"""
        msg_type = raw_data.get("MsgType", "text")
        from_user = raw_data.get("FromUserName", "unknown")
        content = raw_data.get("Content", "")
        image_url = raw_data.get("PicUrl")

        if msg_type == "event":
            content = f"小程序事件: {raw_data.get('Event', '')}"

        user_id = await self._resolve_mini_user(from_user)

        return ChannelMessage(
            query=content,
            user_id=user_id,
            tenant_id="default",
            channel="wechat_mini",
            image_url=image_url,
            metadata={
                "msg_type": msg_type,
                "openid": from_user,
                "raw": raw_data,
            },
        )

    async def verify_signature(self, **kwargs) -> bool:
        # 小程序由微信服务端保证安全，不需要额外签名验证
        return True

    async def build_reply(self, response_text: str, original_msg: ChannelMessage) -> Dict:
        """构建小程序 JSON 回复（客服消息格式）"""
        return {
            "touser": original_msg.metadata.get("openid", ""),
            "msgtype": "text",
            "text": {"content": response_text},
        }

    async def _resolve_mini_user(self, openid: str) -> str:
        """小程序 OpenID → 内部 user_id"""
        try:
            from auth.database import SessionLocal
            from auth.models import User
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.wechat_openid == openid).first()
                if user:
                    return user.id
                import uuid
                new_id = str(uuid.uuid4())
                db.add(User(
                    id=new_id,
                    phone=f"miniapp_{openid[:16]}",
                    nickname=f"小程序用户{openid[-6:]}",
                    wechat_openid=openid,
                    tenant_id="default",
                ))
                db.commit()
                return new_id
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"小程序用户映射失败: {e}")
            return openid
