from urllib.parse import quote_plus
from config.utils import config_manager

# 获取聚合后的配置
raw_config = config_manager.get_auth_config()

class Settings:
    # --- JWT ---
    jwt = raw_config.get("jwt", {})
    SECRET_KEY = jwt.get("secret_key")
    ALGORITHM = jwt.get("algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(jwt.get("expire_minutes", 1440))

    # --- Redis ---
    redis = raw_config.get("redis", {})
    REDIS_HOST = redis.get("host")
    REDIS_PORT = int(redis.get("port", 6379))
    REDIS_PASSWORD = redis.get("password")
    REDIS_DB = 0

    # --- SMS ---
    sms = raw_config.get("sms", {})
    SMS_EXPIRE_SECONDS = int(sms.get("expire_seconds", 300))
    ALI_SMS_URL = sms.get("ali_url")
    ALI_SMS_CODE = sms.get("ali_code")
    # 新增：短信模板ID (默认使用你提供的测试模板)
    ALI_SMS_TEMPLATE_ID = sms.get("template_id", "CST_ptdie100")
    # --- Database (自动构建连接 URL) ---
    db = raw_config.get("database", {})

    # 构建 PostgreSQL 连接串
    if db.get("type") == "postgresql":
        # 密码特殊字符转义
        _pwd = quote_plus(str(db.get("password")))
        DATABASE_URL = (
            f"postgresql://{db.get('user')}:{_pwd}"
            f"@{db.get('host')}:{db.get('port')}/{db.get('name')}"
        )
    else:
        # 默认回退
        DATABASE_URL = "sqlite:///./users.db"

settings = Settings()
