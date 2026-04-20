import httpx
from common.logging import get_logger
from .config import settings

logger = get_logger("auth_sms")

async def send_ali_sms(phone: str, code: str) -> bool:
    """
    发送阿里云短信 (异步)
    :param phone: 手机号
    :param code: 验证码
    :return: 是否发送成功
    """
    if not settings.ALI_SMS_CODE or not settings.ALI_SMS_URL:
        logger.warning("未配置阿里云短信 AppCode 或 URL，跳过发送")
        return False

    # 构造请求头
    headers = {
        "Authorization": f"APPCODE {settings.ALI_SMS_CODE}",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    # 构造请求体 (根据你提供的 API 要求)
    # 注意：content 格式必须与模板要求一致，测试模板通常要求 "code:xxxx"
    data = {
        "content": f"code:{code}",
        "template_id": settings.ALI_SMS_TEMPLATE_ID,
        "phone_number": phone
    }

    try:
        async with httpx.AsyncClient(verify=False) as client:  # verify=False 对应原代码的 ctx.verify_mode = ssl.CERT_NONE
            logger.info(f"正在向 {phone} 发送短信...")
            
            response = await client.post(
                settings.ALI_SMS_URL,
                data=data,
                headers=headers,
                timeout=10.0
            )
            
            # 解析响应
            if response.status_code == 200:
                resp_json = response.json()
                # 不同的服务商返回结构不同，这里假设 status 为 OK 或 success
                # 根据该 API 市场的常见返回：{"status": "OK", ...}
                if resp_json.get("status") == "OK" or resp_json.get("success") is True:
                    logger.info(f"短信发送成功: {resp_json}")
                    return True
                else:
                    logger.error(f"短信发送失败 (API返回错误): {resp_json}")
                    return False
            else:
                logger.error(f"短信发送失败 (HTTP {response.status_code}): {response.text}")
                return False

    except Exception as e:
        logger.error(f"短信发送出现异常: {e}")
        return False