import asyncio
from datetime import datetime
from typing import List, Dict, Any
import logging
import aiohttp
from collections import Counter

from trustcall import create_extractor
from langchain_openai import ChatOpenAI

from .user_profile_models import (
    SessionProfile, SessionMetrics, TechnicalContext, 
    ContentAnalysis, ShoppingInteraction, UserAttributeInference,
    DailyProfile, DailyInteractionMetrics, DailyBehaviorPattern, DailyBusinessUsage,
    LongTermSemanticAnalysis
)


logger = logging.getLogger(__name__)

class SemanticExtractor:   
    def __init__(self, llm_client: ChatOpenAI):
        self.llm = llm_client
        
        self.content_extractor = create_extractor(
            self.llm,
            tools=[ContentAnalysis],
            tool_choice="ContentAnalysis",
            enable_inserts=False
        )
        
        # 将原 service_extractor 替换为 shopping_extractor
        self.shopping_extractor = create_extractor(
            self.llm,
            tools=[ShoppingInteraction],
            tool_choice="ShoppingInteraction", 
            enable_inserts=False
        )
        
        self.attribute_extractor = create_extractor(
            self.llm,
            tools=[UserAttributeInference],
            tool_choice="UserAttributeInference",
            enable_inserts=False
        )
        
        # 长期语义分析提取器
        self.longterm_extractor = create_extractor(
            self.llm,
            tools=[LongTermSemanticAnalysis],
            tool_choice="LongTermSemanticAnalysis",
            enable_inserts=False
        )
    
    async def extract_session_semantics(
        self, 
        conversation_history: List[Dict[str, Any]],
        technical_context: TechnicalContext
    ):
        """提取完整的会话语义信息（电商版）"""
        try:
            conversation_text = self._format_conversation(conversation_history)
            
            # 并行提取内容分析、电商交互和用户属性
            content_task = self._extract_content_analysis(conversation_text)
            shopping_task = self._extract_shopping_interaction(conversation_text)
            attribute_task = self._extract_user_attributes(conversation_text, technical_context)
            
            content_analysis, shopping_interaction, user_attributes = await asyncio.gather(
                content_task, shopping_task, attribute_task
            )
            
            return content_analysis, shopping_interaction, user_attributes
            
        except Exception as e:
            logger.error(f"会话语义提取失败: {str(e)}")
            return None, None, None
    
    
    async def _extract_content_analysis(self, conversation_text: str) -> ContentAnalysis:
        """提取对话内容分析（电商语境）"""
        prompt = f"""
        从以下电商客服对话中分析用户的语言风格、情感状态和核心关注点，提取结构化信息。
        对话内容：
        <conversation>
        {conversation_text}
        </conversation>

        请分析：
        1. 语言和交流风格：使用的语言、提问风格（简洁、详细、急躁等）、整体情感倾向。如果用户抱怨物流慢或货不对板，注意捕捉“愤怒”或“焦虑”情绪。
        2. 情感状态量化：焦虑指数（如催发货场景）、满意度（基于问题是否解决）。
        3. 核心关键词：提取商品名、物流公司、优惠券、活动名称等电商专属词汇。
        4. 讨论话题：如售前咨询、催发货、退换货、发票问题等。
        5. 解决状态：问题是否在此次对话中得到解决，或是否需要升级人工。

        注意：
        - 情感分数要客观，基于具体的语言表现（如使用感叹号、催促词汇）。
        - 所有枚举值必须精确匹配模型定义。
        """
        
        result = await asyncio.to_thread(
            self.content_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        
        return result["responses"][0] if result and result.get("responses") else ContentAnalysis()

    async def _extract_shopping_interaction(self, conversation_text: str) -> ShoppingInteraction:
        """提取电商购物交互信息（订单、商品、意图）"""
        prompt = f"""
        从以下电商客服对话中提取结构化的购物交互信息。
        对话内容：
        <conversation>
        {conversation_text}
        </conversation>

        请详细提取：
        1. 订单信息：识别对话中提到的所有订单号。
        2. 商品信息：提取用户咨询或抱怨的具体商品名称、特征（如颜色、尺码）以及是否已购买。
        3. 服务意图：明确用户的具体售后/售前诉求（如：售前咨询、催发货、查物流、退款、换货等），并判断该意图的当前处理状态。

        注意：
        - 订单号通常为一串数字或带特定前缀的字符。
        - 意图分类必须从预定义选项中选择（如果无匹配项选“其他”）。
        - 保持用户原始表达，不要过度解释商品名称。
        """
        
        result = await asyncio.to_thread(
            self.shopping_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        
        return result["responses"][0] if result and result.get("responses") else ShoppingInteraction()
    
    async def _extract_user_attributes(self, conversation_text: str, technical_context: TechnicalContext) -> UserAttributeInference:
        """推断电商用户属性"""
        prompt = f"""
        基于以下电商客服对话，推断买家的基本属性。

        ##对话内容：
        <conversation>
        {conversation_text}
        </conversation>
        ##当前用户的技术环境信息：
        <technical_context>
        {technical_context.model_dump_json()}
        </technical_context>

        请基于对话语境推断：
        1. 顾客类型：判断是新客咨询、老客复购、羊毛党（过度关注极小额优惠/好评返现）、企业采购还是买来送礼的。
        2. 用户角色：判断是买家本人、收件人（如别人买给自己）、还是代购/分销商。
        3. 推断置信度：基于信息清晰度综合评估（0-1）。

        注意：
        - 只有有明确依据（如话术“第一次买”、“帮朋友问”、“能不能开发票我报销”）时才进行推断。
        - 置信度要反映推断的可靠程度。
        """
        
        result = await asyncio.to_thread(
            self.attribute_extractor.invoke,
            {"messages": [{"role": "user", "content": prompt}]}
        )
        return result["responses"][0] if result and result.get("responses") else UserAttributeInference()
    
    async def extract_longterm_semantics(self, daily_profiles: List[DailyProfile]) -> 'LongTermSemanticAnalysis':
        """提取长期语义分析（电商深度洞察）"""
        if not daily_profiles:
            logger.warning("没有每日画像数据进行长期语义分析")
            return self._create_default_longterm_analysis()
        
        try:
            aggregated_data = self._aggregate_daily_profiles_for_analysis(daily_profiles)
            
            analysis_prompt = f"""
            基于以下电商买家的长期行为数据进行深度语义分析，提取结构化洞察信息：
            
            ## 分析数据概览：
            - 分析周期：{len(daily_profiles)} 天
            - 总会话数：{aggregated_data['total_sessions']}
            - 转人工倾向均值：{aggregated_data['avg_human_transfer']:.2f}
            
            ## 行为模式汇总：
            - 平均情感分数：{aggregated_data['avg_sentiment']:.2f}
            - 平均焦急指数：{aggregated_data['avg_anxiety']:.2f}
            - 高频关键词：{aggregated_data['frequent_keywords']}
            - 核心话题分布：{aggregated_data['topic_distribution']}
            
            ## 业务交互概览：
            - 历史查询订单总数：{aggregated_data['total_orders_queried']}
            - 历史咨询商品总数：{aggregated_data['total_products_inquired']}
            - 发起售后/退换货总数：{aggregated_data['total_after_sales']}
            
            ## 分析要求：
            请基于以上数据进行深度分析，提取以下信息：
            
            1. **确认的买家类型**：基于长期行为（如高频退换货可能是挑剔客，频繁问优惠可能是羊毛党，高频买单不废话是优质老客）。
            2. **核心需求列表**：如“追求正品保障”、“要求极速物流”、“喜欢要赠品”、“对包装要求高”等。
            3. **行为洞察**：如“习惯夜间购物”、“喜欢讨价还价”、“一言不合就要求转人工”、“属于易差评体质”等。
            4. **导购与挽回策略建议**：
               - 若用户退货率高，建议“推荐运费险或详细核对尺码”。
               - 若用户价格敏感，建议“主动推送隐藏优惠券”。
               - 沟通话术建议（如：需要情绪安抚、还是少废话直接丢链接）。
            5. **置信度评估**：基于数据量判断分析是否可靠(0-1)。
            """
            
            result = await asyncio.to_thread(
                self.longterm_extractor.invoke,
                {"messages": [{"role": "user", "content": analysis_prompt}]}
            )
            
            longterm_analysis = result["responses"][0] if result and result.get("responses") else self._create_default_longterm_analysis()
            logger.info(f"长期语义分析完成，置信度: {longterm_analysis.confidence_level:.2f}")
            return longterm_analysis
            
        except Exception as e:
            logger.error(f"长期语义分析失败: {str(e)}")
            return self._create_default_longterm_analysis()
    
    def _aggregate_daily_profiles_for_analysis(self, daily_profiles: List[DailyProfile]) -> Dict[str, Any]:
        """聚合每日画像数据用于分析（适配电商指标）"""
        total_sessions = sum(p.interaction_metrics.total_sessions for p in daily_profiles)
        
        sentiment_scores = [p.behavior_pattern.avg_sentiment_score for p in daily_profiles]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        anxiety_scores = [p.behavior_pattern.avg_anxiety_score for p in daily_profiles]
        avg_anxiety = sum(anxiety_scores) / len(anxiety_scores) if anxiety_scores else 0.0

        human_transfer_rates = [p.behavior_pattern.human_transfer_rate for p in daily_profiles]
        avg_human_transfer = sum(human_transfer_rates) / len(human_transfer_rates) if human_transfer_rates else 0.0
        
        all_keywords = []
        topic_counts = {}
        
        total_orders_queried = 0
        total_products_inquired = 0
        total_after_sales = 0
        
        for profile in daily_profiles:
            all_keywords.extend(profile.behavior_pattern.frequent_keywords)
            for topic, count in profile.behavior_pattern.topic_trends.items():
                topic_counts[topic] = topic_counts.get(topic, 0) + count
                
            # 累加业务指标
            total_orders_queried += profile.business_usage.orders_queried
            total_products_inquired += profile.business_usage.products_inquired
            total_after_sales += profile.business_usage.after_sales_requested
        
        frequent_keywords = [item[0] for item in Counter(all_keywords).most_common(15)]
        
        return {
            'total_sessions': total_sessions,
            'avg_sentiment': avg_sentiment,
            'avg_anxiety': avg_anxiety,
            'avg_human_transfer': avg_human_transfer,
            'frequent_keywords': frequent_keywords,
            'topic_distribution': dict(Counter(topic_counts).most_common(10)),
            'total_orders_queried': total_orders_queried,
            'total_products_inquired': total_products_inquired,
            'total_after_sales': total_after_sales
        }
    
    
    def _create_default_longterm_analysis(self) -> 'LongTermSemanticAnalysis':
        """创建默认的长期分析结果（电商版）"""
        return LongTermSemanticAnalysis(
            confirmed_customer_type="常规买家",
            core_needs=["常规商品咨询", "物流查询"],
            behavioral_insights=["无明显异常行为特征"],
            sales_recommendations=["保持标准客服接待流程"],
            confidence_level=0.3
        )
    
    def _format_conversation(self, conversation_history: List[Dict[str, Any]]) -> str:
        """格式化对话历史"""
        formatted_lines = []
        for item in conversation_history:
            query = item.get('query', '')
            response = item.get('response', '')
            created_at = item.get('created_at', '')
            
            if query:
                formatted_lines.append(f"[{created_at}] 买家: {query}")
            if response:
                formatted_lines.append(f"[{created_at}] 客服: {response}")
        
        return "\n".join(formatted_lines)

    

class SessionMetricsCalculator:
    """会话指标计算器 - 纯数据计算 (通用)"""
    def __init__(self):
        pass
    
    def calculate_session_metrics(
        self, 
        conversation_history: List[Dict[str, Any]]
    ) -> SessionMetrics:
        """计算会话基础指标"""
        user_messages = [msg for msg in conversation_history if msg.get('role') == 'user']
        system_messages = [msg for msg in conversation_history if msg.get('role') == 'assistant']
        
        start_time = None
        end_time = None
        if conversation_history:
            try:
                start_time = datetime.fromisoformat(conversation_history[0].get('created_at', ''))
                end_time = datetime.fromisoformat(conversation_history[-1].get('created_at', ''))
            except:
                start_time = datetime.now()
                end_time = None
        
        duration_seconds = None
        if start_time and end_time:
            duration_seconds = int((end_time - start_time).total_seconds())
        
        avg_response_time = 2.0 if system_messages else None
        day = start_time.strftime('%Y-%m-%d') if start_time else datetime.now().strftime('%Y-%m-%d')
        
        return SessionMetrics(
            start_time=start_time or datetime.now(),
            end_time=end_time or datetime.now(),
            day=day,
            duration_seconds=duration_seconds or 0,
            turn_count=len(conversation_history),
            user_messages_count=len(user_messages),
            system_responses_count=len(system_messages),
            avg_response_time=avg_response_time or 0.0
        )

class DataProfileAnalyzer:   
    async def extract_technical_context(self, conversation_history: List[Dict[str, Any]]) -> TechnicalContext:
        """提取技术环境信息 - 数据提取"""
        first_msg = conversation_history[0] if conversation_history else {}
        metadata = first_msg.get('metadata', {})
        ip_location = {}
        if metadata.get('query_ip'):
            ip_location = await self.get_ip_location(metadata.get('query_ip'))
            
        return TechnicalContext(
            source=metadata.get('query_source',''),
            device=metadata.get('query_device',''),
            ip=metadata.get('query_ip',''),
            country=ip_location.get('country',''),
            province=ip_location.get('province',''),
            city=ip_location.get('city',''),
            longitude=ip_location.get('longitude',0),
            latitude=ip_location.get('latitude',0),
            network_type=metadata.get('network_type',''),
        )
    async def get_ip_location(self, ip: str) -> Dict[str, Any]:
        """异步获取IP地理位置信息"""
        url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    
            if data['status'] == 'success':
                return {
                    "IP": ip,
                    "country": data.get('country'),
                    "province": data.get('regionName'),
                    "city": data.get('city'),
                    "longitude": data.get('lon'),
                    "latitude": data.get('lat')
                }
            else:
                return self._default_location(ip)
        except Exception as e:
            logger.error(f"IP定位解析失败: {e}")
            return self._default_location(ip)
            
    def _default_location(self, ip: str) -> Dict[str, Any]:
        return {"IP": ip, "country": "中国", "province": "未知", "city": "未知", "longitude": 0, "latitude": 0}
class BehaviorAggregator:
    """行为数据聚合器 - 将多个会话聚合为每日电商画像"""
    
    def aggregate_daily_profile(self, session_profiles: List[SessionProfile]) -> DailyProfile:
        """聚合每日画像"""
        if not session_profiles:
            raise ValueError("没有提供会话数据用于聚合")
            
        total_sessions = len(session_profiles)
        total_turns = sum(s.session_metrics.turn_count for s in session_profiles)
        
        # 1. 聚合交互指标
        interaction_metrics = DailyInteractionMetrics(
            total_sessions=total_sessions,
            total_turns=total_turns,
            avg_session_duration=sum(s.session_metrics.duration_seconds for s in session_profiles) / total_sessions / 60 if total_sessions > 0 else 0.0,
            peak_hours=list(set([s.session_metrics.start_time.hour for s in session_profiles])),
            source_distribution=dict(Counter([s.technical_context.source for s in session_profiles if s.technical_context.source]))
        )
        
        # 2. 聚合行为模式
        sentiments = [s.content_analysis.satisfaction_score for s in session_profiles]
        anxieties = [s.content_analysis.anxiety_score for s in session_profiles]
        
        all_keywords = []
        for s in session_profiles:
            all_keywords.extend(s.content_analysis.keywords)
            
        topic_trends = dict(Counter([topic for s in session_profiles for topic in s.content_analysis.topics]))
        
        # 粗略判断转人工率(基于解决状态是否为"需要跟进/升级人工")
        human_transfers = sum(1 for s in session_profiles if s.content_analysis.resolution_status == "需要跟进/升级人工")
        
        behavior_pattern = DailyBehaviorPattern(
            avg_sentiment_score=sum(sentiments) / len(sentiments) if sentiments else 0.5,
            avg_anxiety_score=sum(anxieties) / len(anxieties) if anxieties else 0.0,
            frequent_keywords=[k[0] for k in Counter(all_keywords).most_common(10)],
            topic_trends=topic_trends,
            resolution_rate=1.0 - (human_transfers / total_sessions) if total_sessions > 0 else 0.0,
            human_transfer_rate=human_transfers / total_sessions if total_sessions > 0 else 0.0
        )
        
        # 3. 聚合电商业务使用指标
        orders_queried = 0
        products_inquired = 0
        after_sales_requested = 0
        
        for s in session_profiles:
            orders_queried += len(s.shopping_interaction.orders)
            products_inquired += len(s.shopping_interaction.products)
            # 统计售后意图（退款、换货、投诉等属于售后）
            after_sales_requested += sum(1 for intent in s.shopping_interaction.service_intents 
                                         if intent.intent_type in ['退款', '退货退款', '换货', '投诉'])
            
        business_usage = DailyBusinessUsage(
            orders_queried=orders_queried,
            products_inquired=products_inquired,
            after_sales_requested=after_sales_requested
        )
        
        return DailyProfile(
            interaction_metrics=interaction_metrics,
            behavior_pattern=behavior_pattern,
            business_usage=business_usage
        )