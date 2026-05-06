import sys
import io
import os

# 强制 UTF-8 I/O（Windows 中文版默认 GBK，必须在任何 import 前执行）
try:
    if hasattr(sys.stdout, "buffer") and sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# HuggingFace 镜像（必须在所有 import 之前设置，否则 huggingface_hub 会缓存默认 endpoint）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_ENDPOINT", "https://hf-mirror.com")

# Starlette Config 在 Windows 上用 GBK 读 .env 会崩溃，必须在 import fastapi 之前打补丁
import starlette.config as _starlette_config
_original_read_file = _starlette_config.Config._read_file
@staticmethod
def _utf8_read_file(file_name):
    file_values = {}
    try:
        with open(file_name, encoding="utf-8") as input_file:
            for line in input_file.readlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    file_values[key] = value
    except FileNotFoundError:
        pass
    return file_values
_starlette_config.Config._read_file = _utf8_read_file

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
import warnings  # noqa: E402

from agents.ecommerce_service import graph_manager, build_ecommerce_service_graph,build_question_recommend_graph,build_business_recommend_graph  # noqa: E402
from agents.ecommerce_service.context_engineering.scheduler import start_memory_scheduler, stop_memory_scheduler  # noqa: E402
from agents.ecommerce_service.context_engineering.memory_manager import memory_manager  # noqa: E402
from common.logging import setup_logger, get_logger  # noqa: E402
from config.factory import get_logger_config, get_app_config, get_directories_config  # noqa: E402
from api.router import api_router  # 导入API路由器  # noqa: E402
from auth import router as auth_router, models as auth_models, database as auth_database  # noqa: E402
warnings.filterwarnings("ignore")

# 获取日志配置并设置日志
logger_config = get_logger_config()
setup_logger(**logger_config)
logger = get_logger("ecommerce_service")

# Lifespan事件管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动事件
    logger.info("正在初始化数据库表结构...")
    # 生产环境建议使用 Alembic，这里为了方便直接建表
    auth_models.Base.metadata.create_all(bind=auth_database.engine)
    logger.info("数据库表结构初始化完成")
    # ----------------------------------
    # 确保必要目录存在
    directories_config = get_directories_config()
    os.makedirs(directories_config.get("logs", "logs"), exist_ok=True)
    try:
        logger.info("正在初始化全局记忆管理器...")
        await memory_manager.initialize()  # <--- 必须加这一行！
        logger.info("全局记忆管理器初始化成功！")
    except Exception as e:
        logger.error(f"严重错误：记忆管理器初始化失败: {e}")
    # 确保上传图片目录存在
    # uploads_dir = os.path.join("static", "uploads")
    # os.makedirs(uploads_dir, exist_ok=True)

    # 注册自定义图
    try:
        logger.info("开始注册图...")
        graph_manager.register_graph("ecommerce_service_graph", build_ecommerce_service_graph())
        logger.info("成功注册 ecommerce_service_graph")

        graph_manager.register_graph("question_recommend_graph", build_question_recommend_graph())
        logger.info("成功注册 question_recommend_graph")

        graph_manager.register_graph("business_recommend_graph", build_business_recommend_graph())
        logger.info("成功注册 business_recommend_graph")

        logger.info(f"所有图注册完成，当前已注册的图：{list(graph_manager._registered_graphs.keys())}")
    except Exception as e:
        logger.error(f"图注册失败：{e}", exc_info=True)
        raise

    # 启动记忆管理调度器（每日凌晨 2:00 聚合画像，每周一凌晨 3:00 深度分析）
    try:
        start_memory_scheduler()
        logger.info("记忆管理调度器已启动")
    except Exception as e:
        logger.error(f"启动记忆管理调度器失败：{e}", exc_info=True)

    logger.info("Application started")
    yield
    # 关闭事件
    try:
        stop_memory_scheduler()
        logger.info("记忆管理调度器已停止")
    except Exception as e:
        logger.error(f"停止记忆管理调度器失败：{e}", exc_info=True)

    logger.info("Application shutting down")

# 获取应用配置
app_config = get_app_config()

app = FastAPI(
    title=app_config.get("title", "智能客户服务系统"),
    description=app_config.get("description", "电商智能客服API"),
    version=app_config.get("version", "1.0.0"),
    lifespan=lifespan
)

# CORS
cors_origins = app_config.get("cors_origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求限流 (防刷 / 防账单爆炸)
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")
# 管理后台 SPA (Vue 3 + Element Plus) — 仅在已构建时启用
import os as _os  # noqa: E402
_admin_dist = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "admin", "dist")
if _os.path.exists(_admin_dist):
    # 1. 先挂载静态资源 (js/css/assets)
    app.mount("/admin/assets", StaticFiles(directory=_os.path.join(_admin_dist, "assets")), name="admin_assets")
    # 2. SPA 回退路由 — 所有 /admin/* 的 HTML 请求返回 index.html
    from fastapi.responses import FileResponse
    @app.get("/admin/{rest:path}", include_in_schema=False)
    async def admin_spa(rest: str = ""):
        return FileResponse(_os.path.join(_admin_dist, "index.html"))
    @app.get("/admin", include_in_schema=False)
    async def admin_root():
        return FileResponse(_os.path.join(_admin_dist, "index.html"))

# 注册API路由
# 1. 认证模块路由 (注册/登录/忘记密码)
app.include_router(auth_router)
# 2. 业务API路由
app.include_router(api_router)

# 添加一个用于查看图结构的辅助函数
def view_graph():
    try:
        graph = build_ecommerce_service_graph()
        # graph = build_business_recommend_graph()
        graph_image = graph.compile().get_graph().draw_mermaid_png()
        with open("main_grap2.png", "wb") as f:
            f.write(graph_image)
    except Exception as e:
        logger.error(f"Error generating graph: {e}")

if __name__ == "__main__":
    import uvicorn
    # view_graph()
    host = app_config.get("host", "0.0.0.0")
    port = app_config.get("port", 8081)

    # uvicorn 默认会给自己配置独立的 handler（只写 stderr 不写文件）。
    # 这里传空 handler + propagate=True，让所有 uvicorn 日志走 root logger 的 file handler
    _uvicorn_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {},
        "loggers": {
            "uvicorn":        {"handlers": [], "propagate": True, "level": "INFO"},
            "uvicorn.error":  {"handlers": [], "propagate": True, "level": "INFO"},
            "uvicorn.access": {"handlers": [], "propagate": True, "level": "INFO"},
        },
    }
    uvicorn.run(app, host=host, port=port, log_config=_uvicorn_log_config)
