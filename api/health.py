"""
健康检查端点 — 返回所有依赖服务的连接状态（全并发，2s 超时）
"""
from fastapi import APIRouter
from pydantic import BaseModel
import time
import os
import asyncio

router = APIRouter(tags=["健康检查"])

TIMEOUT = 2  # 单个检查超时（秒）

class HealthStatus(BaseModel):
    status: str = "ok"
    uptime_seconds: float = 0
    checks: dict = {}

_start_time = time.time()


async def _check_postgres() -> dict:
    try:
        import asyncpg
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=os.getenv("DB_HOST", "47.106.22.90"),
                port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_DATABASE", "test"),
                timeout=TIMEOUT,
            ),
            timeout=TIMEOUT + 0.5,
        )
        await asyncio.wait_for(conn.execute("SELECT 1"), timeout=TIMEOUT)
        await conn.close()
        return {"status": "ok"}
    except asyncio.TimeoutError:
        return {"status": "degraded", "error": "response timeout"}
    except Exception as e:
        return {"status": "down", "error": str(e)[:80]}


async def _check_chromadb() -> dict:
    result = {"status": "down"}
    try:
        import httpx
        host = os.getenv("CHROMA_HOST", "47.106.22.90")
        port = os.getenv("CHROMA_PORT", "8000")
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"http://{host}:{port}/api/v2")
        result = {"status": "ok" if resp.status_code == 200 else "degraded"}
    except Exception as e:
        result["error"] = str(e)[:80]

    # 附加熔断器状态
    try:
        from agents.ecommerce_service.context_engineering.chroma_health import get_chroma_health
        result["circuit"] = get_chroma_health().stats()
    except Exception:
        result["circuit"] = {"healthy": False, "circuit_open": False}
    return result


async def _check_llm() -> dict:
    """LLM 检查：只验证模型配置是否存在（不发真实请求）"""
    try:
        from config.utils import config_manager
        cfg = config_manager.get_agents_config().get("llm", {})
        model = cfg.get("model", "unknown")
        if model and cfg.get("base_url") and cfg.get("api_key"):
            return {"status": "ok", "model": model}
        return {"status": "degraded", "model": model, "error": "missing api_key or base_url"}
    except Exception as e:
        return {"status": "down", "error": str(e)[:80]}


async def _check_redis() -> dict:
    try:
        import redis.asyncio as aioredis
        r = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            socket_connect_timeout=TIMEOUT,
        )
        await asyncio.wait_for(r.ping(), timeout=TIMEOUT)
        await r.close()
        return {"status": "ok"}
    except asyncio.TimeoutError:
        return {"status": "degraded", "error": "response timeout"}
    except Exception as e:
        return {"status": "down", "error": str(e)[:80]}


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """全栈健康检查 — 4 项并发，最多 3s 返回"""
    results = await asyncio_gather_or_none(
        _check_postgres(),
        _check_chromadb(),
        _check_llm(),
        _check_redis(),
    )

    checks = {
        "postgres":  results[0] or {"status": "unknown"},
        "chromadb":  results[1] or {"status": "unknown"},
        "llm":       results[2] or {"status": "unknown"},
        "redis":     results[3] or {"status": "unknown"},
    }

    down = sum(1 for c in checks.values() if c.get("status") == "down")
    status = "down" if down >= 3 else "degraded" if down >= 1 else "ok"

    return HealthStatus(
        status=status,
        uptime_seconds=round(time.time() - _start_time, 1),
        checks=checks,
    )


async def asyncio_gather_or_none(*coros):
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"status": "error", "error": str(r)[:80]} for r in results]
