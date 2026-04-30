"""
P1-3: 平台 Token 自动续期定时任务
每天凌晨 2:00 检查所有租户的平台凭据，过期前 3 天自动刷新
"""
import asyncio
from datetime import datetime, timedelta
from common.logging import get_logger

logger = get_logger("scheduler.token_refresh")


async def refresh_all_tokens():
    """遍历所有租户，刷新即将过期的平台 Token"""
    from agents.ecommerce_service.channels.platforms.credential import (
        get_expiring_credentials, save_credential
    )
    from agents.ecommerce_service.channels.platforms import get_adapter

    expiring = await get_expiring_credentials(days=3)
    if not expiring:
        logger.debug("没有即将过期的凭据")
        return

    logger.info(f"发现 {len(expiring)} 个即将过期的凭据，开始刷新...")
    for cred in expiring:
        try:
            adapter = get_adapter(cred.platform)
            if not adapter:
                continue
            adapter.credential = cred
            new_cred = await adapter.refresh_token()
            await save_credential(cred.platform, new_cred)  # 使用 platform 作为 tenant_id 的简化
            logger.info(f"Token 刷新成功: {cred.platform}")
        except Exception as e:
            logger.error(f"Token 刷新失败 [{cred.platform}]: {e}")


async def start_token_refresh_scheduler():
    """
    启动 Token 续期调度器（每天凌晨 2:00 执行）
    可在 main.py 的 lifespan 中调用
    """
    async def _loop():
        while True:
            now = datetime.now()
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            logger.info(f"Token 续期调度器: 下次执行 {next_run.strftime('%Y-%m-%d %H:%M:%S')} (等待 {wait_seconds:.0f}s)")
            await asyncio.sleep(wait_seconds)
            try:
                await refresh_all_tokens()
            except Exception as e:
                logger.error(f"Token 续期任务异常: {e}")

    asyncio.create_task(_loop())
    logger.info("Token 续期调度器已启动")
