"""
健康检查端点 — 返回所有依赖服务的连接状态
"""
from fastapi import APIRouter
from pydantic import BaseModel
import time
import os

router = APIRouter(tags=["健康检查"])


class HealthStatus(BaseModel):
    status: str = "ok"       # "ok" / "degraded" / "down"
    uptime_seconds: float = 0
    checks: dict = {}


_start_time = time.time()


async def _check_postgres() -> dict:
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host=os.getenv("DB_HOST", "47.106.22.90"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "123456"),
            database=os.getenv("DB_DATABASE", "test"),
            timeout=5,
        )
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "ok", "latency_ms": round((time.time() - _start_time) * 1000)}
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}


async def _check_chromadb() -> dict:
    try:
        import httpx
        host = os.getenv("CHROMA_HOST", "47.106.22.90")
        port = os.getenv("CHROMA_PORT", "8000")
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"http://{host}:{port}/api/v2")
        return {"status": "ok" if resp.status_code == 200 else "degraded", "code": resp.status_code}
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}


async def _check_llm() -> dict:
    try:
        from agents.ecommerce_service.core import base_model
        await base_model.ainvoke("ping")
        return {"status": "ok", "model": getattr(base_model, "model_name", "?")}
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}


async def _check_redis() -> dict:
    try:
        import redis.asyncio as aioredis
        r = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            socket_connect_timeout=3,
        )
        await r.ping()
        await r.close()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "down", "error": str(e)[:100]}


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """全栈健康检查 — DB / ChromaDB / LLM / Redis"""
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
    import asyncio
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"status": "error", "error": str(r)[:100]} for r in results]
