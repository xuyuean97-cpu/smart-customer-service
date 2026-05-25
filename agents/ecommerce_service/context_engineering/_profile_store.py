# Auto-generated mixin — extracted from memory_manager.py
from common.logging import get_logger
import json
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ._memory_core import MemoryType, _get_profile_extractor
from .profile.user_profile_models import SessionProfile, DailyProfile, InsightProfile

logger = get_logger("memory._profile_store")

# Redis 缓存 TTL（秒）
PROFILE_CACHE_TTL = 300  # 5 分钟

_redis = None


def _get_redis():
    """懒加载 Redis 异步连接"""
    global _redis
    if _redis is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        import redis.asyncio as aioredis
        _redis = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD") or None,
            socket_connect_timeout=2,
            decode_responses=False,
        )
    return _redis


def _cache_key(user_id: str, application_id: str = "") -> str:
    return f"profile_cache:{user_id}:{application_id or 'default'}"


class ProfileStoreMixin:
    async def get_user_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户画像（Redis 缓存加速）
        ① Redis 命中 → <10ms 返回
        ② ChromaDB 深度/每日/会话画像 → 命中则写 Redis 并返回
        ③ 都没有 → LLM 实时提取 → 写 Redis 并返回
        """
        if not self._initialized:
            await self.initialize()

        import json as _json
        app_id = application_id or "电商主智能客服"
        cache_k = _cache_key(user_id, app_id)

        # ── 0. 优先查 Redis 缓存 ──
        try:
            rds = _get_redis()
            cached = await rds.get(cache_k)
            if cached:
                await rds.expire(cache_k, PROFILE_CACHE_TTL)  # 续期
                logger.info(f"画像缓存命中: {user_id}")
                return _json.loads(cached)
        except Exception as e:
            logger.debug(f"Redis 读取失败（不影响主流程）: {e}")

        profile = None
        try:
            # ── 1. ChromaDB: 深度洞察 ──
            deep_profiles = await self.get_deep_profiles(user_id=user_id, application_id=application_id, limit=1)
            if deep_profiles and len(deep_profiles) > 0:
                profile_obj = deep_profiles[0].get("profile")
                profile = profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj

            # ── 2. ChromaDB: 每日画像 ──
            if not profile:
                daily_profiles = await self.get_daily_profiles(user_id=user_id, application_id=application_id, limit=1)
                if daily_profiles and len(daily_profiles) > 0:
                    profile_obj = daily_profiles[0].get("profile")
                    profile = profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj

            # ── 3. ChromaDB: 会话画像 ──
            if not profile:
                session_profiles = await self.get_session_profiles(user_id=user_id, application_id=application_id, limit=1)
                if session_profiles and len(session_profiles) > 0:
                    profile_obj = session_profiles[0].get("profile")
                    profile = profile_obj.model_dump() if hasattr(profile_obj, 'model_dump') else profile_obj

            # ── 4. LLM 实时提取 ──
            if not profile:
                logger.info(f"ChromaDB 无画像缓存，LLM 实时提取: {user_id}")
                profile = await self.extract_user_profile(user_id=user_id, application_id=application_id)

        except Exception as e:
            logger.error(f"获取用户画像失败: {e}", exc_info=True)
            return None

        # ── 写 Redis 缓存（任意来源获取成功后） ──
        if profile:
            try:
                payload = _json.dumps(profile, ensure_ascii=False, default=str)
                await _get_redis().setex(cache_k, PROFILE_CACHE_TTL, payload)
                logger.info(f"画像已缓存到 Redis: {user_id} (TTL={PROFILE_CACHE_TTL}s)")
            except Exception as e:
                logger.warning(f"Redis 写入失败（不影响主流程）: {e}")

        return profile
    async def extract_user_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        提取用户画像
        从用户的对话历史中大模型实时分析并生成完整维度的用户画像
        """
        if not self._initialized:
            await self.initialize()

        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None

            # 获取用户最近的对话历史
            conversation_history = await self.get_conversation_history(
                application_id=application_id,
                user_id=user_id,
                limit=100
            )

            if not conversation_history:
                logger.warning(f"未找到用户对话数据无法提取画像: {user_id}")
                return None

            # 尝试调用提取器提取完整的用户画像
            if hasattr(extractor, 'extract_complete_profile'):
                profile = await extractor.extract_complete_profile(
                    user_id=user_id,
                    conversation_history=conversation_history
                )
            elif hasattr(extractor, 'extract_user_profile'):
                profile = await extractor.extract_user_profile(
                    user_id=user_id,
                    conversation_history=conversation_history
                )
            else:
                # 兜底：使用会话画像作为基础
                profile = await extractor.extract_session_profile(
                    conversation_history=conversation_history
                )

            # 如果返回的是 Pydantic 模型，转为 dict
            profile_dict = profile.model_dump() if hasattr(profile, 'model_dump') else profile
            logger.info(f"实时大模型提取用户画像成功: {user_id}")
            return profile_dict

        except Exception as e:
            logger.error(f"提取用户画像失败: {str(e)}", exc_info=True)
            return None

    async def trigger_session_profile_extraction(
        self,
        user_id: str,
        run_id: str,
        application_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        触发买家单次会话画像提取（第一步）
        """
        if not self._initialized:
            await self.initialize()
        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("电商画像提取器不可用")
                return None

            conversation_history = await self.get_conversation_history(
                application_id=application_id,
                user_id=user_id,
                run_id=run_id,
                limit=1000
            )
            if not conversation_history:
                logger.warning(f"未找到会话数据: {application_id}:{user_id}:{run_id}")
                return None

            # 提取单次会话画像
            session_profile = await extractor.extract_session_profile(
                conversation_history=conversation_history
            )

            # 存储买家会话画像到记忆系统
            await self.store_session_profile(
                user_id=user_id,
                application_id=application_id,
                run_id=run_id,
                session_profile=session_profile
            )

            logger.info(f"买家会话画像提取完成: {user_id}:{run_id}")

            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "run_id": run_id,
                "profile": session_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"会话画像提取失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "application_id": application_id,
                "user_id": user_id,
                "run_id": run_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def trigger_daily_profile_aggregation(
        self,
        application_id: str,
        user_id: str,
        date: str
    ) -> Optional[Dict[str, Any]]:
        """
        触发每日画像聚合（第二步）

        Args:
            user_id: 用户ID
            application_id: 应用ID
            date: 日期 (YYYY-MM-DD)

        Returns:
            聚合结果
        """
        if not self._initialized:
            await self.initialize()

        try:
            # 获取画像提取器
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None

            # 获取当日所有会话画像
            session_profiles= await self.get_session_profiles(
            user_id=user_id,
            application_id=application_id,
            day=date
            )

            if len(session_profiles)<1:
                logger.warning(f"未找到当日会话画像: {user_id}:{date}")
                return None

            # 聚合每日画像
            daily_profile = await extractor.extract_daily_profile(
                session_profiles=[p.get("profile") for p in session_profiles]
            )

            # 存储每日画像
            await self.store_daily_profile(
                user_id=user_id,
                application_id=application_id,
                date=date,
                daily_profile=daily_profile
            )

            logger.info(f"每日画像聚合完成: {user_id}:{date}")

            return {
                "success": True,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "profile": daily_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"每日画像聚合失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "user_id": user_id,
                "application_id": application_id,
                "date": date,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def trigger_deep_insight_analysis(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        触发买家生命周期深度洞察（第三步）
        """
        if not self._initialized:
            await self.initialize()

        try:
            extractor = _get_profile_extractor()
            if not extractor:
                logger.error("画像提取器不可用")
                return None

            daily_profiles = await self.get_period_daily_profiles(user_id, application_id, days)

            # 电商场景下互动频次高，3天即可出初步洞察
            if len(daily_profiles) < 3:
                logger.warning(f"数据不足进行深度分析: {user_id}, 仅有{len(daily_profiles)}天数据")
                return None

            analysis_period = f"{days}天"
            deep_profile = await extractor.extract_insight_profile(
                user_id=user_id,
                daily_profiles=daily_profiles,
                analysis_period=analysis_period
            )

            await self.store_deep_profile(
                user_id=user_id,
                application_id=application_id,
                analysis_period=analysis_period,
                deep_profile=deep_profile
            )

            logger.info(f"买家深度洞察完成: {user_id}")

            return {
                "success": True,
                "user_id": user_id,
                "profile": deep_profile.model_dump(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"深度洞察分析失败: {str(e)}", exc_info=True)
            return {"success": False, "user_id": user_id, "error": str(e), "timestamp": datetime.now().isoformat()}


    # ============================== 画像存储和查询辅助方法 (电商重构版) ==============================

    async def store_session_profile(
        self,
        user_id: str,
        application_id: Optional[str] = None,
        run_id: Optional[str] = None,
        session_profile: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储单次买家会话画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}

        try:
            # 获取用户意图(售前、催发货、退款等)
            service_intents = [intent.intent_type for intent in getattr(session_profile.shopping_interaction, 'service_intents', [])]

            profile_metadata = {
                "agent_memory_type": MemoryType.USER_SESSION_PROFILE.value,
                "application_id": application_id,
                "start_time": str(session_profile.session_metrics.start_time),
                "end_time": str(session_profile.session_metrics.end_time),
                "day": session_profile.session_metrics.day,
                "duration_seconds": session_profile.session_metrics.duration_seconds,
                "turn_count": session_profile.session_metrics.turn_count,

                # 技术上下文
                "source": session_profile.technical_context.source,
                "device": session_profile.technical_context.device,
                "ip": session_profile.technical_context.ip,
                "province": session_profile.technical_context.province,
                "city": session_profile.technical_context.city,

                # 内容与情感分析
                "sentiment": session_profile.content_analysis.sentiment.value if hasattr(session_profile.content_analysis.sentiment, 'value') else session_profile.content_analysis.sentiment,
                "anxiety_score": session_profile.content_analysis.anxiety_score,
                "keywords": json.dumps(session_profile.content_analysis.keywords, ensure_ascii=False),
                "topics": json.dumps(session_profile.content_analysis.topics, ensure_ascii=False),
                "resolution_status": session_profile.content_analysis.resolution_status.value if hasattr(session_profile.content_analysis.resolution_status, 'value') else session_profile.content_analysis.resolution_status,

                # 电商购物交互 (订单、商品、售后意图)
                "orders": json.dumps(session_profile.shopping_interaction.queried_orders, ensure_ascii=False),
                "products": json.dumps(session_profile.shopping_interaction.inquired_products, ensure_ascii=False),
                "service_intents": json.dumps(service_intents, ensure_ascii=False),

                # 用户属性推断
                "confidence": session_profile.inferred_user_attribute.confidence,
                "customer_type": session_profile.inferred_user_attribute.customer_type.value if hasattr(session_profile.inferred_user_attribute.customer_type, 'value') else session_profile.inferred_user_attribute.customer_type,
                "role": session_profile.inferred_user_attribute.role.value if hasattr(session_profile.inferred_user_attribute.role, 'value') else session_profile.inferred_user_attribute.role,

                "profile": json.dumps(session_profile.model_dump(mode='json'), ensure_ascii=False, default=str)
            }

            messages = [
                {"role": "user", "content": f"买家 {user_id} 会话 {run_id} 的电商购物画像"},
                {"role": "assistant", "content": f"已提取画像: 情感={profile_metadata.get('sentiment')}, 类型={profile_metadata.get('customer_type')}, 关键词={profile_metadata.get('keywords')}"}
            ]

            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                run_id=run_id,
                metadata={**base_metadata, **profile_metadata},
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"电商会话画像已存储: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"存储电商会话画像失败: {e}", exc_info=True)
            raise

    async def get_session_profiles(
        self,
        application_id: Optional[str] = None,
        user_id: Optional[str] = None,
        run_id: Optional[str] = None,
        day: Optional[str] = None,
        sentiment: Optional[str] = None,
        anxiety_score: Optional[float] = None,
        resolution_status: Optional[str] = None,
        orders: Optional[List[str]] = None,
        products: Optional[List[str]] = None,
        service_intents: Optional[List[str]] = None,
        customer_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取买家单次会话画像记录"""
        if not self._initialized:
            await self.initialize()

        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_SESSION_PROFILE.value}}]

            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if run_id:
                filter_conditions.append({"run_id": {"$eq": run_id}})
            if day:
                filter_conditions.append({"day": {"$eq": day}})
            if sentiment:
                filter_conditions.append({"sentiment": {"$eq": sentiment}})
            if anxiety_score:
                filter_conditions.append({"anxiety_score": {"$gte": anxiety_score}})
            if resolution_status:
                filter_conditions.append({"resolution_status": {"$eq": resolution_status}})

            # 电商专属查询过滤
            if orders:
                filter_conditions.append({"orders": {"$in": orders}})
            if products:
                filter_conditions.append({"products": {"$in": products}})
            if service_intents:
                filter_conditions.append({"service_intents": {"$in": service_intents}})
            if customer_type:
                filter_conditions.append({"customer_type": {"$eq": customer_type}})

            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)

            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories

            session_profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                profile_json = metadata.get('profile', '')
                if profile_json:
                    try:
                        # from .user_profile_models import SessionProfile
                        session_profiles.append({
                            "memory_id": memory.get('id'),
                            "user_id": memory.get('user_id'),
                            "application_id": metadata.get('application_id', ''),
                            "run_id": memory.get('run_id', ''),
                            "profile": SessionProfile(**json.loads(profile_json))
                        })
                    except Exception as e:
                        logger.warning(f"解析SessionProfile失败: {e}")

            return session_profiles
        except Exception as e:
            logger.error(f"获取会话画像历史失败: {e}", exc_info=True)
            return []

    async def store_daily_profile(
        self,
        user_id: str,
        application_id: str,
        date: str,
        daily_profile: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储买家每日统计画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}

        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DAILY_PROFILE.value,
                "application_id": application_id,
                "date": date,

                "total_sessions": daily_profile.interaction_metrics.total_sessions,
                "total_turns": daily_profile.interaction_metrics.total_turns,

                "avg_sentiment_score": daily_profile.behavior_pattern.avg_sentiment_score,
                "avg_anxiety_score": daily_profile.behavior_pattern.avg_anxiety_score,
                "resolution_rate": daily_profile.behavior_pattern.resolution_rate,
                "human_transfer_rate": daily_profile.behavior_pattern.human_transfer_rate,
                "topic_trends": json.dumps(daily_profile.behavior_pattern.topic_trends, ensure_ascii=False),

                # 电商每日业务统计
                "orders_queried": daily_profile.business_usage.orders_queried,
                "products_inquired": daily_profile.business_usage.products_inquired,
                "after_sales_requested": daily_profile.business_usage.after_sales_requested,

                "profile": json.dumps(daily_profile.model_dump(), ensure_ascii=False)
            }

            messages = [{"role": "system", "content": f"买家 {user_id} 在 {date} 的每日电商行为画像"}]

            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            return memory_id

        except Exception as e:
            logger.error(f"存储每日画像失败: {e}", exc_info=True)
            raise
    async def get_daily_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        date: Optional[str] = None,
        human_transfer_rate: Optional[float] = None,
        orders_queried: Optional[int] = None,
        after_sales_requested: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取买家每日画像历史"""
        if not self._initialized:
            await self.initialize()

        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_DAILY_PROFILE.value}}]

            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if date:
                filter_conditions.append({"date": {"$eq": date}})
            if human_transfer_rate:
                filter_conditions.append({"human_transfer_rate": {"$gte": human_transfer_rate}})
            if orders_queried:
                filter_conditions.append({"orders_queried": {"$gte": orders_queried}})
            if after_sales_requested:
                filter_conditions.append({"after_sales_requested": {"$gte": after_sales_requested}})

            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)

            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories

            profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    profiles.append({
                        "memory_id": memory.get('id'),
                        "user_id": memory.get('user_id'),
                        "application_id": metadata.get('application_id', ''),
                        "date": metadata.get('date', ''),
                        "profile": DailyProfile(**json.loads(metadata.get('profile')))
                    })
            return profiles
        except Exception as e:
            logger.error(f"获取每日画像失败: {e}", exc_info=True)
            return []
    async def get_deep_profiles(
        self,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        analysis_period: Optional[str] = None,
        primary_customer_type: Optional[str] = None,
        spending_power: Optional[str] = None,
        customer_value_score: Optional[float] = None,
        churn_risk: Optional[float] = None,
        upsell_potential: Optional[float] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取深度电商画像历史"""
        if not self._initialized:
            await self.initialize()

        try:
            filter_conditions = [{"agent_memory_type": {"$eq": MemoryType.USER_DEEP_PROFILE.value}}]

            if user_id:
                filter_conditions.append({"user_id": {"$eq": user_id}})
            if application_id:
                filter_conditions.append({"application_id": {"$eq": application_id}})
            if analysis_period:
                filter_conditions.append({"analysis_period": {"$eq": analysis_period}})
            if primary_customer_type:
                filter_conditions.append({"primary_customer_type": {"$eq": primary_customer_type}})
            if spending_power:
                filter_conditions.append({"spending_power": {"$eq": spending_power}})
            if customer_value_score:
                filter_conditions.append({"customer_value_score": {"$gte": customer_value_score}})
            if churn_risk:
                filter_conditions.append({"churn_risk": {"$gte": churn_risk}})
            if upsell_potential:
                filter_conditions.append({"upsell_potential": {"$gte": upsell_potential}})

            filters = filter_conditions[0] if len(filter_conditions) == 1 else {"$and": filter_conditions}
            result = await self.profile_memory.get_all(filters=filters, limit=limit)

            all_memories = result.get('results', []) if isinstance(result, dict) else []
            import inspect
            if inspect.iscoroutine(all_memories):
                all_memories = await all_memories

            profiles = []
            for memory in all_memories:
                metadata = memory.get('metadata', {})
                if metadata.get('profile'):
                    profiles.append({
                        "memory_id": memory.get('id'),
                        "user_id": memory.get('user_id'),
                        "application_id": metadata.get('application_id', ''),
                        "analysis_period": metadata.get('analysis_period', ''),
                        "profile": InsightProfile(**json.loads(metadata.get('profile')))
                    })
            return profiles

        except Exception as e:
            logger.error(f"获取深度画像失败: {e}", exc_info=True)
            return []

    async def store_deep_profile(
        self,
        user_id: str,
        application_id: str,
        analysis_period: str,
        deep_profile: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """存储电商买家深度生命周期画像"""
        if not self._initialized:
            await self.initialize()
        base_metadata = deepcopy(metadata) if metadata else {}

        try:
            profile_metadata = {
                "agent_memory_type": MemoryType.USER_DEEP_PROFILE.value,
                "application_id": application_id,
                "analysis_period": analysis_period,

                # 电商核心标签
                "primary_customer_type": deep_profile.primary_customer_type.value if hasattr(deep_profile.primary_customer_type, 'value') else deep_profile.primary_customer_type,
                "spending_power": deep_profile.spending_power.value if hasattr(deep_profile.spending_power, 'value') else deep_profile.spending_power,

                # 购物与服务偏好
                "preferred_categories": json.dumps(deep_profile.shopping_pattern.preferred_categories, ensure_ascii=False),
                "purchase_frequency": deep_profile.shopping_pattern.purchase_frequency,
                "price_sensitivity": deep_profile.shopping_pattern.price_sensitivity,
                "prefers_self_service": deep_profile.service_preference.prefers_self_service,

                # 电商商业价值
                "customer_value_score": deep_profile.customer_value_score,
                "churn_risk": deep_profile.churn_risk,
                "upsell_potential": deep_profile.upsell_potential,
                "recommended_categories": json.dumps(deep_profile.recommended_categories, ensure_ascii=False),
                "communication_strategy": deep_profile.communication_strategy,

                "profile": json.dumps(deep_profile.model_dump(), ensure_ascii=False)
            }

            messages = [{"role": "system", "content": f"买家 {user_id} 的电商深度洞察画像，分析周期: {analysis_period}"}]

            result = await self.profile_memory.add(
                messages=messages,
                user_id=user_id,
                metadata={**base_metadata, **profile_metadata},
                infer=False
            )
            memory_id = result.get('results', [{}])[0].get('id') if result.get('results') else None
            logger.info(f"电商深度画像已存储: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"存储深度画像失败: {e}", exc_info=True)
            raise

    async def get_period_daily_profiles(self, user_id: str, application_id: str, days: int) -> List[Any]:
        """获取买家指定时期的每日画像"""
        try:
            daily_profiles = []
            from datetime import timezone
            end_date = datetime.now(timezone.utc)
            for i in range(days):
                date = end_date - timedelta(days=i)
                daily_profile = await self.get_daily_profiles(
                    user_id=user_id,
                    application_id=application_id,
                    date=date.strftime("%Y-%m-%d")
                )
                if daily_profile:
                    daily_profiles.append(daily_profile[0].get("profile"))

            logger.info(f"获取到买家 {user_id} 最近 {days} 天的 {len(daily_profiles)} 个每日画像")
            return daily_profiles
        except Exception as e:
            logger.error(f"获取时期每日画像失败: {e}", exc_info=True)
            return []

    def _reconstruct_profile_object(self, profile_data: Dict[str, Any], profile_type: str):
        """根据电商画像类型重构对象"""
        try:
            if profile_type == "session":
                return SessionProfile(**profile_data)
            elif profile_type == "daily":
                return DailyProfile(**profile_data)
            elif profile_type in ["deep", "deep_insight"]:
                return InsightProfile(**profile_data)
            return None
        except Exception as e:
            logger.warning(f"重构{profile_type}画像失败: {e}")
            return None

    def reconstruct_session_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['SessionProfile']:
        """
        从查询记录中重构电商买家单次会话画像 (SessionProfile) 对象列表

        Args:
            records: 记忆系统查询结果记录列表

        Returns:
            SessionProfile对象列表
        """
        session_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                session_profile = self._reconstruct_profile_object(profile_data, "session")
                if session_profile:
                    session_profiles.append(session_profile)

        logger.info(f"成功重构了 {len(session_profiles)} 个买家会话画像(SessionProfile)对象")
        return session_profiles

    def reconstruct_daily_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['DailyProfile']:
        """
        从查询记录中重构电商买家每日统计画像 (DailyProfile) 对象列表

        Args:
            records: 记忆系统查询结果记录列表

        Returns:
            DailyProfile对象列表
        """
        daily_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                daily_profile = self._reconstruct_profile_object(profile_data, "daily")
                if daily_profile:
                    daily_profiles.append(daily_profile)

        logger.info(f"成功重构了 {len(daily_profiles)} 个买家每日画像(DailyProfile)对象")
        return daily_profiles

    def reconstruct_insight_profiles_from_records(self, records: List[Dict[str, Any]]) -> List['InsightProfile']:
        """
        从查询记录中重构电商买家深度生命周期洞察画像 (InsightProfile) 对象列表

        Args:
            records: 记忆系统查询结果记录列表

        Returns:
            InsightProfile对象列表
        """
        insight_profiles = []
        for record in records:
            profile_data = record.get('profile_data', {})
            if profile_data:
                insight_profile = self._reconstruct_profile_object(profile_data, "deep_insight")
                if insight_profile:
                    insight_profiles.append(insight_profile)

        logger.info(f"成功重构了 {len(insight_profiles)} 个买家深度画像(InsightProfile)对象")
        return insight_profiles
