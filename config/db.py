"""
统一数据库连接配置 — 所有模块共用，杜绝硬编码密码
"""
import os


def get_db_config() -> dict:
    """从环境变量读取数据库连接参数"""
    return {
        "host": os.getenv("DB_HOST", "47.106.22.90"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_DATABASE", "test"),
        "timeout": int(os.getenv("DB_TIMEOUT", "10")),
    }
