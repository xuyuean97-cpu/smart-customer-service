from fastapi import APIRouter
from .chat import ecommerce_router
from .summary import router as summary_router
from .text2sql_training import router as text2sql_training_router
from .image_upload import image_router
from .question_recommend import router as question_recommend_router
from .business_recommend import router as business_recommend_router
from .memory_management import router as memory_management_router
from .text2qa import router as text2qa_router
from .dashboard import router as dashboard_router
from .health import router as health_router
from agents.ecommerce_service.tools.jd_order_sync import router as jd_sync_router
from .wechat_callback import router as wechat_router
from .ticket import router as ticket_router
from .platform_callback import router as platform_router
from .evaluation import router as evaluation_router
from .platform_management import router as platform_management_router

api_router = APIRouter()
api_router.include_router(evaluation_router)
api_router.include_router(platform_management_router)
api_router.include_router(health_router)
api_router.include_router(jd_sync_router)
api_router.include_router(platform_router)
api_router.include_router(dashboard_router)
api_router.include_router(wechat_router)
api_router.include_router(ticket_router)
api_router.include_router(ecommerce_router)
api_router.include_router(summary_router)
api_router.include_router(text2sql_training_router)
api_router.include_router(image_router)
api_router.include_router(question_recommend_router)
api_router.include_router(business_recommend_router)
api_router.include_router(memory_management_router)
api_router.include_router(text2qa_router)
