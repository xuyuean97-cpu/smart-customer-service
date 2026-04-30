"""
电商版用户画像调度系统
负责协调买家会话级、每日和长期生命周期的自动化分析与画像生成
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .user_profile_models import ProfileUpdateResult
from .profile_extractor import create_profile_extractor
from .operational_analytics import OperationalAnalyticsEngine

logger = logging.getLogger(__name__)

@dataclass
class ScheduleConfig:
    """电商画像调度配置"""
    enable_session_extraction: bool = True       # 会话结束即时提取订单、意图
    enable_daily_aggregation: bool = True        # 每日凌晨聚合转人工率、售后率
    enable_deep_analysis: bool = True            # 每周计算买家LTV、流失风险
    enable_operational_reports: bool = True      # 自动生成电商运营报告

    # 调度时间配置
    daily_aggregation_time: str = "01:00"        # 每日凌晨1点进行当天数据结账
    deep_analysis_day: int = 0                   # 周一进行买家深度分析
    deep_analysis_time: str = "02:00"            # 凌晨2点

    # 触发条件配置
    session_timeout_minutes: int = 30            # 超过30分钟未说话视为会话结束，触发提取
    min_deep_analysis_days: int = 3              # 深度分析最少需要的天数(电商频次较高，改为3天即可)

    # 并发控制
    max_concurrent_extractions: int = 10         # 最大并发大模型调用数
    batch_size: int = 50                         # 批处理大小

@dataclass
class ConversationData:
    """电商买家对话数据封装"""
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    start_time: datetime
    end_time: Optional[datetime] = None
    technical_context: Dict[str, Any] = None

class ProfileScheduler:
    """电商智能客服 - 用户画像自动调度器"""

    def __init__(self, config: ScheduleConfig = None, llm_client = None):
        self.config = config or ScheduleConfig()
        self.scheduler = AsyncIOScheduler()

        # 引入电商版的提取器和分析引擎
        self.profile_extractor = create_profile_extractor(llm_client)
        self.analytics_engine = OperationalAnalyticsEngine()

        # 活跃买家会话跟踪池
        self.active_sessions: Dict[str, datetime] = {}
        self.pending_extractions: Dict[str, ConversationData] = {}

        # 并发控制锁
        self.extraction_semaphore = asyncio.Semaphore(self.config.max_concurrent_extractions)

        # 生命周期回调函数钩子 (供外部存入数据库使用)
        self.session_end_callbacks: List[Callable] = []
        self.daily_update_callbacks: List[Callable] = []
        self.deep_analysis_callbacks: List[Callable] = []

    def start(self):
        """启动电商画像调度引擎"""
        try:
            if self.config.enable_daily_aggregation:
                self._schedule_daily_aggregation()
            if self.config.enable_deep_analysis:
                self._schedule_deep_analysis()
            if self.config.enable_operational_reports:
                self._schedule_operational_reports()

            self._schedule_session_timeout_check()

            self.scheduler.start()
            logger.info("🛒 电商买家画像调度系统已启动")

        except Exception as e:
            logger.error(f"调度系统启动失败: {str(e)}")
            raise

    def stop(self):
        try:
            self.scheduler.shutdown()
            logger.info("电商买家画像调度系统已停止")
        except Exception as e:
            logger.error(f"调度系统停止失败: {str(e)}")

    def _schedule_daily_aggregation(self):
        hour, minute = map(int, self.config.daily_aggregation_time.split(':'))
        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self._run_daily_aggregation, trigger=trigger, id='daily_aggregation',
            name='每日买家画像及指标聚合', max_instances=1, replace_existing=True
        )
        logger.info(f"已调度 [每日电商聚合] 任务，执行时间：每天 {self.config.daily_aggregation_time}")

    def _schedule_deep_analysis(self):
        hour, minute = map(int, self.config.deep_analysis_time.split(':'))
        trigger = CronTrigger(day_of_week=self.config.deep_analysis_day, hour=hour, minute=minute)
        self.scheduler.add_job(
            self._run_deep_analysis, trigger=trigger, id='deep_analysis',
            name='买家生命周期深度分析(LTV/流失预警)', max_instances=1, replace_existing=True
        )
        logger.info(f"已调度 [深度洞察] 任务，执行时间：每周{self.config.deep_analysis_day} {self.config.deep_analysis_time}")

    def _schedule_operational_reports(self):
        # 每日报表 (包含转人工率、售后率预警)
        daily_trigger = CronTrigger(hour=23, minute=30)
        self.scheduler.add_job(
            self._generate_daily_report, trigger=daily_trigger, id='daily_report',
            name='电商客服每日打烊报表', max_instances=1, replace_existing=True
        )
        # 周度大盘报表
        weekly_trigger = CronTrigger(day_of_week=6, hour=8, minute=0)
        self.scheduler.add_job(
            self._generate_weekly_report, trigger=weekly_trigger, id='weekly_report',
            name='电商客服周运营总结', max_instances=1, replace_existing=True
        )

    def _schedule_session_timeout_check(self):
        trigger = IntervalTrigger(minutes=5)
        self.scheduler.add_job(
            self._check_session_timeouts, trigger=trigger, id='session_timeout_check',
            name='买家会话离线检测', max_instances=1, replace_existing=True
        )

    async def track_session_activity(self, user_id: str, session_id: str, message_data: Dict[str, Any]):
        """在用户聊天时不断调用此方法，重置超时计时器并追加聊天记录"""
        try:
            session_key = f"{user_id}:{session_id}"
            self.active_sessions[session_key] = datetime.now()

            if session_key not in self.pending_extractions:
                self.pending_extractions[session_key] = ConversationData(
                    session_id=session_id, user_id=user_id, messages=[],
                    start_time=datetime.now(), technical_context=message_data.get('technical_context', {})
                )
            self.pending_extractions[session_key].messages.append(message_data)
        except Exception as e:
            logger.error(f"买家会话跟踪失败: {str(e)}")

    async def trigger_session_end(self, user_id: str, session_id: str):
        """外部主动触发结束（例如用户点击了“结束服务”或“转人工”）"""
        try:
            session_key = f"{user_id}:{session_id}"
            if session_key in self.pending_extractions:
                conversation = self.pending_extractions[session_key]
                conversation.end_time = datetime.now()
                asyncio.create_task(self._process_session_extraction(conversation))
                self.active_sessions.pop(session_key, None)
                self.pending_extractions.pop(session_key, None)
                logger.info(f"会话结束(主动触发)，进入画像提取队列: 买家 {user_id}")
        except Exception as e:
            logger.error(f"主动触发会话结束失败: {str(e)}")

    async def _check_session_timeouts(self):
        """扫描长时间未说话的买家，判定为咨询结束，送入大模型提取订单/诉求"""
        try:
            current_time = datetime.now()
            timeout_threshold = timedelta(minutes=self.config.session_timeout_minutes)
            timeout_sessions = []

            for session_key, last_activity in self.active_sessions.items():
                if current_time - last_activity > timeout_threshold:
                    timeout_sessions.append(session_key)

            for session_key in timeout_sessions:
                if session_key in self.pending_extractions:
                    conversation = self.pending_extractions[session_key]
                    conversation.end_time = current_time
                    asyncio.create_task(self._process_session_extraction(conversation))
                    logger.info(f"会话静默超时，进入画像提取队列: {session_key}")

                self.active_sessions.pop(session_key, None)
                self.pending_extractions.pop(session_key, None)
        except Exception as e:
            logger.error(f"会话超时检测异常: {str(e)}")

    async def _process_session_extraction(self, conversation: ConversationData):
        """调用 LLM 提取买家单次咨询的商品、订单及售后意图"""
        async with self.extraction_semaphore:
            try:
                if not self.config.enable_session_extraction:
                    return

                conversation_history = []
                for msg in conversation.messages:
                    conversation_history.append({
                        'role': msg.get('role', 'user'),
                        'query': msg.get('content', ''),
                        'response': msg.get('response', ''),
                        'created_at': msg.get('timestamp', datetime.now().isoformat()),
                        'metadata': conversation.technical_context
                    })

                # 调用重构后的提取器 (移除了旧版的不兼容参数)
                result = await self.profile_extractor.extract_session_profile(
                    conversation_history=conversation_history
                )

                if result:
                    # 抛给上层应用（如保存到 MongoDB / Redis）
                    for callback in self.session_end_callbacks:
                        try:
                            await callback(conversation, result)
                        except Exception as e:
                            logger.error(f"会话结束回调执行失败: {str(e)}")
                    logger.info(f"✅ 买家 {conversation.user_id} 单次画像提取完成 (意图: {len(result.shopping_interaction.service_intents)}个)")

            except Exception as e:
                logger.error(f"单次会话画像提取失败: {str(e)}")

    async def _run_daily_aggregation(self):
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            users_to_process = await self._get_active_buyers_for_date(yesterday)
            logger.info(f"开始生成每日买家聚合指标，日期：{yesterday}，买家数：{len(users_to_process)}")

            for i in range(0, len(users_to_process), self.config.batch_size):
                batch = users_to_process[i:i + self.config.batch_size]
                tasks = [self._process_daily_aggregation(user_id, yesterday) for user_id in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                success_count = sum(1 for r in results if isinstance(r, ProfileUpdateResult) and r.success)

            logger.info(f"每日买家画像聚合完成，成功：{success_count}/{len(users_to_process)}")
        except Exception as e:
            logger.error(f"每日聚合任务失败: {str(e)}")

    async def _process_daily_aggregation(self, user_id: str, date: str) -> ProfileUpdateResult:
        async with self.extraction_semaphore:
            try:
                session_profiles = await self._get_session_profiles_for_user_date(user_id, date)
                if not session_profiles:
                    return ProfileUpdateResult(user_id=user_id, update_type="daily", success=False, error_message="当日无咨询")

                # 调用重构后的方法：计算买家当日转人工率、售后倾向等
                daily_profile = await self.profile_extractor.extract_daily_profile(
                    session_profiles=session_profiles
                )

                if daily_profile:
                    for callback in self.daily_update_callbacks:
                        await callback(user_id, date, daily_profile)

                    return ProfileUpdateResult(user_id=user_id, update_type="daily", success=True)
            except Exception as e:
                return ProfileUpdateResult(user_id=user_id, update_type="daily", success=False, error_message=str(e))

    async def _run_deep_analysis(self):
        try:
            users_to_analyze = await self._get_buyers_for_deep_analysis()
            logger.info(f"开始买家深度洞察(推测购买力、流失风险)，目标用户数：{len(users_to_analyze)}")

            for i in range(0, len(users_to_analyze), self.config.batch_size):
                batch = users_to_analyze[i:i + self.config.batch_size]
                tasks = [self._process_deep_analysis(user_id) for user_id in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("买家深度分析批次完成")
        except Exception as e:
            logger.error(f"深度分析任务失败: {str(e)}")

    async def _process_deep_analysis(self, user_id: str) -> ProfileUpdateResult:
        async with self.extraction_semaphore:
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                daily_profiles = await self._get_daily_profiles_for_user_period(
                    user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
                )

                if len(daily_profiles) < self.config.min_deep_analysis_days:
                    return ProfileUpdateResult(user_id=user_id, update_type="deep_insight", success=False, error_message="历史互动数据不足以进行深度归纳")

                # 提取客户价值、购买偏好、流失率
                insight_profile = await self.profile_extractor.extract_insight_profile(
                    user_id=user_id,
                    daily_profiles=daily_profiles,
                    analysis_period=f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )

                if insight_profile:
                    for callback in self.deep_analysis_callbacks:
                        await callback(user_id, insight_profile)

                    return ProfileUpdateResult(
                        user_id=user_id, update_type="deep_insight", success=True,
                        confidence_score=insight_profile.profile_confidence
                    )
            except Exception as e:
                return ProfileUpdateResult(user_id=user_id, update_type="deep_insight", success=False, error_message=str(e))

    async def _generate_daily_report(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            report = await self.analytics_engine.generate_operational_report(today, "daily")
            logger.info(f"📊 电商每日运营大盘报告已生成: {report.report_id}")
            # 这里可以接企业微信/飞书/钉钉机器人的 Webhook 进行播报
        except Exception as e:
            logger.error(f"每日大盘报告生成失败: {str(e)}")

    async def _generate_weekly_report(self):
        try:
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            period = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"

            report = await self.analytics_engine.generate_operational_report(period, "weekly")
            logger.info(f"📊 电商周度运营大盘报告已生成: {report.report_id}")
        except Exception as e:
            logger.error(f"周报生成失败: {str(e)}")

    # ================= 数据库 Mock 访问层 (实际项目中需要被替换) =================
    async def _get_active_buyers_for_date(self, date: str) -> List[str]:
        """获取指定日期有过咨询的买家ID"""
        return [f"buyer_{i}" for i in range(1, 11)]

    async def _get_buyers_for_deep_analysis(self) -> List[str]:
        """获取符合深度分析条件(如近期频发售后)的买家ID"""
        return [f"buyer_{i}" for i in range(1, 6)]

    async def _get_session_profiles_for_user_date(self, user_id: str, date: str):
        """从 DB 加载该买家当日的会话记录"""
        return []

    async def _get_daily_profiles_for_user_period(self, user_id: str, start_date: str, end_date: str):
        """从 DB 加载该买家指定时间段的日统计"""
        return []

    # ================= 外部回调注册与状态监控 =================
    def add_session_end_callback(self, callback: Callable): self.session_end_callbacks.append(callback)
    def add_daily_update_callback(self, callback: Callable): self.daily_update_callbacks.append(callback)
    def add_deep_analysis_callback(self, callback: Callable): self.deep_analysis_callbacks.append(callback)

    async def manual_daily_aggregation(self, user_id: str, date: str) -> ProfileUpdateResult:
        return await self._process_daily_aggregation(user_id, date)

    async def manual_deep_analysis(self, user_id: str) -> ProfileUpdateResult:
        return await self._process_deep_analysis(user_id)

    def get_scheduler_status(self) -> Dict[str, Any]:
        return {
            "running": self.scheduler.running,
            "active_buyers_online": len(self.active_sessions),
            "pending_llm_extractions": len(self.pending_extractions),
            "scheduled_jobs": [
                {"name": job.name, "next_run": job.next_run_time.isoformat() if job.next_run_time else None}
                for job in self.scheduler.get_jobs()
            ]
        }


# ============================== 全局实例 ==============================
profile_scheduler = ProfileScheduler()
