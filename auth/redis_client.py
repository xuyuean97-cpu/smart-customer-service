import redis
from .config import settings

# 创建 Redis 连接池
pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True  # 自动解码为字符串
)

redis_client = redis.Redis(connection_pool=pool)

def set_sms_code(phone: str, code: str):
    """保存验证码 (5分钟过期)"""
    key = f"auth:sms:{phone}"
    redis_client.setex(key, settings.SMS_EXPIRE_SECONDS, code)

def get_sms_code(phone: str) -> str:
    """获取验证码"""
    key = f"auth:sms:{phone}"
    return redis_client.get(key)

def delete_sms_code(phone: str):
    """删除验证码"""
    key = f"auth:sms:{phone}"
    redis_client.delete(key)
    
def check_sms_cooldown(phone: str) -> bool:
    """检查是否处于冷却期 (返回 True 表示需要等待)"""
    key = f"auth:sms:cooldown:{phone}"
    return redis_client.exists(key) > 0

def set_sms_cooldown(phone: str, seconds: int = 60):
    """设置冷却时间 (默认60秒)"""
    key = f"auth:sms:cooldown:{phone}"
    # 值设为 "1" 即可，关键是过期时间
    redis_client.setex(key, seconds, "1")