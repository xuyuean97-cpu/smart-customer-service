"""
电商版运营分析引擎
提供用户分群、漏斗分析、售后风险识别及交叉销售洞察
"""

from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass
import logging
from collections import Counter

from .user_profile_models import (
    BusinessInsight, OperationalReport, DailyProfile, InsightProfile,
    SpendingPower
)

logger = logging.getLogger(__name__)

@dataclass
class AnalyticsConfig:
    """分析配置"""
    segment_min_users: int = 10
    insight_confidence_threshold: float = 0.7
    trend_analysis_days: int = 7
    value_score_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.value_score_weights is None:
            self.value_score_weights = {
                "frequency": 0.4,       # 购买/咨询频率
                "satisfaction": 0.3,    # 满意度
                "retention": 0.3        # 留存率/未退货率
            }

class UserSegmentationEngine:
    """电商用户分群引擎"""

    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.segment_definitions = {
            "高价值VIP买家": {
                "conditions": ["spending_power=高价值客户/高客单价", "customer_type=VIP会员", "value_score>0.7"],
                "description": "消费能力强、客单价高且忠诚度高的核心用户"
            },
            "忠实老客": {
                "conditions": ["customer_type=老客", "value_score>0.5"],
                "description": "有稳定复购习惯的常规买家"
            },
            "高潜新客": {
                "conditions": ["customer_type=新客", "upsell_potential>0.6"],
                "description": "刚开始接触品牌且转化潜力较高的新用户"
            },
            "羊毛党/价格敏感": {
                "conditions": ["customer_type=羊毛党/价格敏感型"],
                "description": "对价格极度敏感，通常在大促或有优惠券时才下单的用户"
            },
            "高频退换/高风险": {
                "conditions": ["churn_risk>0.7", "satisfaction<0.5"],
                "description": "经常发起退换货、有差评倾向或较高流失风险的客户"
            },
            "犹豫未转化客": {
                "conditions": ["customer_type=潜在/浏览未下单客户", "upsell_potential>0.4"],
                "description": "频繁咨询商品但迟迟未下单的客户"
            }
        }

    async def segment_users(self, user_profiles: List[InsightProfile]) -> Dict[str, List[str]]:
        """执行用户分群"""
        segments = {name: [] for name in self.segment_definitions.keys()}

        for profile in user_profiles:
            for segment_name, criteria in self.segment_definitions.items():
                if self._matches_criteria(profile, criteria["conditions"]):
                    segments[segment_name].append(profile.user_id)

        # 过滤掉用户数太少的分群
        return {
            name: users for name, users in segments.items()
            if len(users) >= self.config.segment_min_users
        }

    def _matches_criteria(self, profile: InsightProfile, conditions: List[str]) -> bool:
        for condition in conditions:
            if not self._evaluate_condition(profile, condition):
                return False
        return True

    def _evaluate_condition(self, profile: InsightProfile, condition: str) -> bool:
        try:
            if "=" in condition:
                field, value = condition.split("=")
                return self._check_equality(profile, field.strip(), value.strip())
            elif ">" in condition:
                field, value = condition.split(">")
                return self._check_greater_than(profile, field.strip(), float(value.strip()))
            elif "<" in condition:
                field, value = condition.split("<")
                return self._check_less_than(profile, field.strip(), float(value.strip()))
            return False
        except Exception as e:
            logger.error(f"条件评估失败: {condition} - {e}")
            return False

    def _check_equality(self, profile: InsightProfile, field: str, value: str) -> bool:
        if field == "spending_power":
            return profile.spending_power.value == value
        elif field == "customer_type":
            return profile.primary_customer_type.value == value
        return False

    def _check_greater_than(self, profile: InsightProfile, field: str, value: float) -> bool:
        if field == "value_score":
            return profile.customer_value_score > value
        elif field == "churn_risk":
            return profile.churn_risk > value
        elif field == "upsell_potential":
            return profile.upsell_potential > value
        return False

    def _check_less_than(self, profile: InsightProfile, field: str, value: float) -> bool:
        if field == "satisfaction":
            # 简化：通过反向的churn_risk评估满意度
            return (1.0 - profile.churn_risk) < value
        return False

class MetricsCalculator:
    """电商核心指标计算器"""

    def __init__(self, config: AnalyticsConfig):
        self.config = config

    def calculate_operational_metrics(
        self,
        daily_profiles: List[DailyProfile],
        insight_profiles: List[InsightProfile]
    ) -> Dict[str, Any]:
        """计算电商客服运营指标"""
        total_users = len(set(p.user_id for p in daily_profiles if hasattr(p, 'user_id'))) if daily_profiles else len(insight_profiles)
        active_users = len([p for p in daily_profiles if p.interaction_metrics.total_sessions > 0])

        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)

        # 计算平均满意度与解决率
        satisfaction_scores = [p.behavior_pattern.avg_sentiment_score for p in daily_profiles if p.behavior_pattern.avg_sentiment_score > 0]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.8

        resolution_rates = [p.behavior_pattern.resolution_rate for p in daily_profiles]
        avg_resolution_rate = sum(resolution_rates) / len(resolution_rates) if resolution_rates else 0.85

        # 电商特色指标
        transfer_rates = [p.behavior_pattern.human_transfer_rate for p in daily_profiles]
        avg_transfer_rate = sum(transfer_rates) / len(transfer_rates) if transfer_rates else 0.15

        total_after_sales = sum(p.business_usage.after_sales_requested for p in daily_profiles)
        refund_inquiry_rate = total_after_sales / total_sessions if total_sessions > 0 else 0.0

        # 估算转化率 (这里用查单量/咨询商品量作为一个简化的转化意向指标)
        total_orders = sum(p.business_usage.orders_queried for p in daily_profiles)
        total_products = sum(p.business_usage.products_inquired for p in daily_profiles)
        estimated_conversion_rate = total_orders / (total_products + 0.1) if total_products > 0 else 0.0
        estimated_conversion_rate = min(estimated_conversion_rate, 1.0) # 封顶100%

        return {
            "total_users": total_users,
            "active_users": active_users,
            "avg_satisfaction": avg_satisfaction,
            "resolution_rate": avg_resolution_rate,
            "transfer_to_human_rate": avg_transfer_rate,
            "refund_inquiry_rate": refund_inquiry_rate,
            "conversion_rate": estimated_conversion_rate,
            "total_after_sales": total_after_sales
        }

class InsightGenerator:
    """电商业务洞察生成器"""

    def __init__(self, config: AnalyticsConfig):
        self.config = config

    async def generate_business_insights(
        self,
        metrics: Dict[str, Any],
        segments: Dict[str, List[str]],
        trend_data: Dict[str, Any]
    ) -> List[BusinessInsight]:
        """生成业务告警与机会洞察"""
        insights = []

        # 洞察1：转人工率异常
        if metrics.get("transfer_to_human_rate", 0) > 0.30:
            insights.append(BusinessInsight(
                insight_type="high_human_transfer",
                title="AI拦截率下降，转人工率偏高",
                description=f"当前转人工率达到{metrics.get('transfer_to_human_rate', 0):.1%}，超过30%警戒线，客服人力压力增大。",
                impact_level="high",
                affected_users=int(metrics.get("active_users", 0) * metrics.get("transfer_to_human_rate", 0)),
                recommended_actions=[
                    "检查近期是否有突发大促活动导致规则复杂化",
                    "补充缺失的商品知识库(如尺码、色差问答)",
                    "优化自动退款/催发货的自助卡片流程"
                ],
                metrics={"transfer_rate": metrics.get("transfer_to_human_rate", 0)}
            ))

        # 洞察2：退款/售后率突增
        if metrics.get("refund_inquiry_rate", 0) > 0.20:
            insights.append(BusinessInsight(
                insight_type="high_after_sales",
                title="售后及退款咨询量激增预警",
                description=f"售后诉求占总咨询的{metrics.get('refund_inquiry_rate', 0):.1%}，表明近期发货可能延误或批次商品存在质量争议。",
                impact_level="high",
                affected_users=metrics.get("total_after_sales", 0),
                recommended_actions=[
                    "紧急排查近期被高频投诉的SKU及批次",
                    "协调仓储物流，向用户批量推送延误安抚短信",
                    "设置快捷退款防线，避免引发平台客诉扣分"
                ],
                metrics={"refund_inquiry_rate": metrics.get("refund_inquiry_rate", 0)}
            ))

        # 洞察3：高潜新客转化机会
        potential_users = len(segments.get("高潜新客", [])) + len(segments.get("犹豫未转化客", []))
        if potential_users > 50:
            insights.append(BusinessInsight(
                insight_type="conversion_opportunity",
                title="存在大量高潜未转化客户",
                description=f"识别到{potential_users}名频繁咨询但犹豫未下单的客户。",
                impact_level="medium",
                affected_users=potential_users,
                recommended_actions=[
                    "针对该人群自动触发【限时首单立减券】",
                    "客服主动发起破冰话术(如：亲亲对尺码不确认吗？)",
                    "强力宣导运费险及七天无理由退换政策消除顾虑"
                ],
                metrics={"potential_users_count": potential_users}
            ))

        return insights

    def generate_recommendations(self, metrics: Dict[str, Any], segments: Dict[str, List[str]], insights: List[BusinessInsight]) -> List[str]:
        recommendations = []

        # 基础兜底建议
        if metrics.get("resolution_rate", 0) < 0.85:
            recommendations.append("丰富商品详情图文问答，提高AI独立导购能力")

        if metrics.get("avg_satisfaction", 0) < 0.75:
            recommendations.append("接入情感分析拦截，在用户暴躁时无条件秒转人工")

        # 根据高优先级洞察提取核心建议
        for insight in insights:
            if insight.impact_level == "high":
                recommendations.extend(insight.recommended_actions[:2])

        # 去重并截断
        return list(dict.fromkeys(recommendations))[:6]

class TrendAnalyzer:
    """电商趋势分析器"""

    def __init__(self, config: AnalyticsConfig):
        self.config = config

    async def analyze_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """分析环比趋势"""
        trends = {}
        if len(historical_data) < 2:
            return {"商品咨询热度": "数据不足", "售后退货倾向": "数据不足", "转人工拦截率": "数据不足"}

        # 转化意向趋势
        conversion_scores = [data.get("conversion_rate", 0) for data in historical_data]
        trends["商品转化意向"] = self._calculate_trend(conversion_scores)

        # 售后趋势 (反向指标，下降是好事)
        refund_scores = [data.get("refund_inquiry_rate", 0) for data in historical_data]
        refund_trend = self._calculate_trend(refund_scores)
        trends["售后退货倾向"] = refund_trend.replace("上升", "恶化(上升)").replace("下降", "改善(下降)")

        # 拦截率趋势 (1 - 转人工率)
        interception_scores = [1.0 - data.get("transfer_to_human_rate", 0) for data in historical_data]
        trends["AI导购拦截率"] = self._calculate_trend(interception_scores)

        return trends

    def _calculate_trend(self, values: List[float]) -> str:
        if len(values) < 2: return "数据不足"
        recent_avg = sum(values[-3:]) / len(values[-3:]) if len(values) >= 3 else values[-1]
        earlier_avg = sum(values[:-3]) / len(values[:-3]) if len(values) > 3 else values[0]

        if recent_avg > earlier_avg * 1.05: return "上升趋势"
        elif recent_avg < earlier_avg * 0.95: return "下降趋势"
        else: return "稳定"

class OperationalAnalyticsEngine:
    """电商优化版运营分析主引擎"""

    def __init__(self, config: AnalyticsConfig = None):
        self.config = config or AnalyticsConfig()
        self.segmentation_engine = UserSegmentationEngine(self.config)
        self.metrics_calculator = MetricsCalculator(self.config)
        self.insight_generator = InsightGenerator(self.config)
        self.trend_analyzer = TrendAnalyzer(self.config)

    async def generate_operational_report(
        self,
        period: str,
        report_type: str = "daily",
        daily_profiles: List[DailyProfile] = None,
        insight_profiles: List[InsightProfile] = None
    ) -> OperationalReport:
        """生成电商客服运营报告"""
        try:
            report_id = f"ECOM_REPORT_{report_type}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            daily_profiles = daily_profiles or []
            insight_profiles = insight_profiles or []

            # 1. 计算电商核心指标
            metrics = self.metrics_calculator.calculate_operational_metrics(daily_profiles, insight_profiles)

            # 2. 用户群体切片
            segments = await self.segmentation_engine.segment_users(insight_profiles)

            # 3. 获取历史数据并分析趋势 (此处使用 mock 数据演示环比)
            historical_data = await self._get_mock_historical_data()
            trends = await self.trend_analyzer.analyze_trends(historical_data)

            # 4. 生成诊断洞察与建议
            key_insights = await self.insight_generator.generate_business_insights(metrics, segments, {})
            recommendations = self.insight_generator.generate_recommendations(metrics, segments, key_insights)

            return OperationalReport(
                report_id=report_id,
                period=period,
                report_type=report_type,
                total_users=metrics["total_users"],
                active_users=metrics["active_users"],
                new_users=len(segments.get("高潜新客", [])),
                retention_rate=1.0 - (metrics["refund_inquiry_rate"] * 0.5), # 简化计算
                avg_satisfaction=metrics["avg_satisfaction"],
                resolution_rate=metrics["resolution_rate"],
                transfer_to_human_rate=metrics["transfer_to_human_rate"],
                conversion_rate=metrics["conversion_rate"],
                refund_inquiry_rate=metrics["refund_inquiry_rate"],
                key_insights=key_insights,
                trends=trends,
                recommendations=recommendations,
                data_sources=["daily_profiles", "insight_profiles"],
                confidence_level=0.90
            )

        except Exception as e:
            logger.error(f"电商运营报告生成失败: {str(e)}")
            raise

    async def analyze_user_behavior_prediction(self, insight_profiles: List[InsightProfile]) -> Dict[str, Any]:
        """电商客户行为与生命周期预测"""
        high_risk_users = [p for p in insight_profiles if p.churn_risk > 0.6]
        high_potential_users = [p for p in insight_profiles if p.upsell_potential > 0.6]

        return {
            "churn_risk_analysis": {
                "high_risk_count": len(high_risk_users),
                "risk_factors": self._analyze_churn_factors(high_risk_users),
                "intervention_recommendations": ["发放无门槛致歉券", "由专属人工客服回访跟进退换货工单"]
            },
            "upsell_opportunities": {
                "target_user_count": len(high_potential_users),
                "recommended_categories": self._analyze_upsell_categories(high_potential_users),
                "expected_revenue_impact": "预估可提升客单价 15-20%"
            }
        }

    def _analyze_churn_factors(self, high_risk_users: List[InsightProfile]) -> List[str]:
        """分析导致退换货或差评的核心原因"""
        factors = []
        if any(u for u in high_risk_users if u.spending_power == SpendingPower.HIGH):
            factors.append("高净值客户体验受损(可能由于物流慢或缺货)")
        if len(high_risk_users) > 5:
            factors.append("批次商品可能存在质量瑕疵导致集中爆发不满")
        return factors

    def _analyze_upsell_categories(self, high_potential_users: List[InsightProfile]) -> List[str]:
        """聚合高潜客户最容易被交叉销售的品类"""
        category_counter = Counter()
        for user in high_potential_users:
            for category in user.recommended_categories:
                category_counter[category] += 1
        return [cat for cat, count in category_counter.most_common(5)]

    async def _get_mock_historical_data(self) -> List[Dict[str, Any]]:
        """从 MemoryManager 获取近期历史指标（优先真实数据，fallback 模拟数据）"""
        try:
            from ..memory_manager import memory_manager
            history = await memory_manager.get_conversation_history(limit=5000)
            if not history:
                return self._default_historical_fallback()

            # 按周分组聚合
            from datetime import datetime, timedelta
            weeks: Dict[str, Dict[str, Any]] = {}
            datetime.now().date()

            for item in history:
                metadata = item.get('metadata', {})
                created = metadata.get('created_at') or item.get('created_at', '')
                if not created:
                    continue
                try:
                    if isinstance(created, str):
                        d = datetime.fromisoformat(created.replace('Z', '+00:00')).date()
                    else:
                        continue
                except Exception:
                    continue

                week_start = (d - timedelta(days=d.weekday())).isoformat()
                if week_start not in weeks:
                    weeks[week_start] = {"total": 0, "transfers": 0}

                weeks[week_start]["total"] += 1
                # 检测是否转人工（可通过 metadata 字段判断）
                resolution = metadata.get('resolution_status', '')
                if resolution in ('需要跟进/升级人工', 'transferred'):
                    weeks[week_start]["transfers"] += 1

            result = []
            for week in sorted(weeks.keys())[-4:]:  # 最近4周
                w = weeks[week]
                total = max(w["total"], 1)
                result.append({
                    "conversion_rate": 0.12,  # 需接入电商平台转化数据
                    "refund_inquiry_rate": 0.08,
                    "transfer_to_human_rate": round(w["transfers"] / total, 3),
                })

            return result if result else self._default_historical_fallback()
        except Exception:
            return self._default_historical_fallback()

    def _default_historical_fallback(self) -> List[Dict[str, Any]]:
        return [
            {"conversion_rate": 0.12, "refund_inquiry_rate": 0.08, "transfer_to_human_rate": 0.25},
            {"conversion_rate": 0.13, "refund_inquiry_rate": 0.10, "transfer_to_human_rate": 0.28},
            {"conversion_rate": 0.11, "refund_inquiry_rate": 0.15, "transfer_to_human_rate": 0.35},
        ]

# ============================== 全局实例 ==============================
operational_analytics_engine = OperationalAnalyticsEngine()
