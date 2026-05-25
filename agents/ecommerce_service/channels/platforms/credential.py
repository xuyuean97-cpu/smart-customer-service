"""
平台授权凭据管理 — 读取 / 写入 / Token 刷新

凭据存储在 tenants 表的 config JSONB 字段中:
  tenants.config.platforms = {
    "jd": { "app_key": "...", "app_secret": "...", "access_token": "...", ... },
    "taobao": { ... }
  }
"""
import json
import time
from typing import Dict, List
from models.platform_order import PlatformCredential
from common.logging import get_logger

logger = get_logger("channels.credential")


async def get_credentials(tenant_id: str) -> Dict[str, PlatformCredential]:
    """获取租户的所有平台凭据"""
    try:
        import asyncpg
        from config.db import get_db_config
        conn = await asyncpg.connect(**get_db_config())
        try:
            row = await conn.fetchrow(
                "SELECT config FROM tenants WHERE id = $1", tenant_id
            )
            if not row or not row["config"]:
                return {}
            config = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"])
            platforms = config.get("platforms", {})
            result = {}
            for name, data in platforms.items():
                result[name] = PlatformCredential(platform=name, **data)
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"读取平台凭据失败: {e}")
        return {}


async def save_credential(tenant_id: str, cred: PlatformCredential):
    """保存单个平台凭据"""
    try:
        import asyncpg
        import os
        import json
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "47.106.22.90"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "123456"),
            database=os.getenv("DB_DATABASE", "test"),
            timeout=10,
        )
        try:
            row = await conn.fetchrow(
                "SELECT config FROM tenants WHERE id = $1", tenant_id
            )
            config = row["config"] if row and row["config"] else {}
            if isinstance(config, str):
                config = json.loads(config)
            if "platforms" not in config:
                config["platforms"] = {}

            cred_dict = cred.model_dump(exclude_none=True)
            cred_dict["updated_at"] = int(time.time())
            config["platforms"][cred.platform] = cred_dict

            await conn.execute(
                "UPDATE tenants SET config = $1 WHERE id = $2",
                json.dumps(config, ensure_ascii=False), tenant_id,
            )
            logger.info(f"凭据已保存: tenant={tenant_id} platform={cred.platform}")
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"保存平台凭据失败: {e}")


async def get_expiring_credentials(days: int = 3) -> List[PlatformCredential]:
    """获取即将过期的凭据列表（供定时任务使用）"""
    try:
        import asyncpg
        import os
        import json
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "47.106.22.90"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "123456"),
            database=os.getenv("DB_DATABASE", "test"),
            timeout=10,
        )
        try:
            rows = await conn.fetch("SELECT id, config FROM tenants WHERE config IS NOT NULL")
            result = []
            now = int(time.time())
            threshold = now + days * 86400
            for row in rows:
                config = row["config"] if isinstance(row["config"], dict) else json.loads(row["config"] or "{}")
                platforms = config.get("platforms", {})
                for name, data in platforms.items():
                    if data.get("expires_at", 0) < threshold:
                        result.append(PlatformCredential(platform=name, **data))
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"查询即将过期凭据失败: {e}")
        return []
