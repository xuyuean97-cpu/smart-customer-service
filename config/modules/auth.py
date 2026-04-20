# 文件路径: config/modules/auth.py
import os

# 读取环境变量，定义 Auth 模块特有的配置
AUTH_CONFIG = {
    "auth": {
        "jwt": {
            # 生产环境务必在 .env 中设置复杂密钥
            "secret_key": os.getenv("AUTH_SECRET_KEY", "default_unsafe_secret_key"),
            "algorithm": os.getenv("AUTH_ALGORITHM", "HS256"),
            "expire_minutes": int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", 1440)),
        },
        "sms": {
            "expire_seconds": int(os.getenv("SMS_CODE_EXPIRE_SECONDS", 300)),
            "ali_url": os.getenv("ALi_SMS_URL"),
            "ali_code": os.getenv("ALi_SMS_CODE"),
        }
    }
}