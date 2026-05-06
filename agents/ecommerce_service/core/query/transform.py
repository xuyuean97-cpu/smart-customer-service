from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from ..models import structed_model as model
from typing import List
from langchain_core.messages import AnyMessage
from common.logging import get_logger
from agents.ecommerce_service.context_engineering.prompts import query_transform_prompts
from datetime import datetime

logger = get_logger("agents.utils.query_transform")




async def rewrite_query(original_query,messages:List[AnyMessage]):
    """
    将用户提出的原始问题重写为更适合电商客服知识库检索的问题。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 改写后的问题（适合检索）
    """
    logger.info(f"开始重写查询: {original_query}")
    query_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_transform_prompts.QUERY_REWRITE_SYSTEM_PROMPT),
        ("human", query_transform_prompts.QUERY_REWRITE_PROMPT)
    ])
    query_rewriter = query_rewrite_prompt | model

    try:

        response = await query_rewriter.ainvoke({"original_query": original_query,"messages": messages})
        rewritten_query = response.content.strip()
        return rewritten_query
    except Exception as e:
        logger.error(f"问题重写失败: {e}")
        return original_query



async def generate_step_back_query(original_query, messages:List[AnyMessage]=None):
    """
    针对原始问题生成一个更泛化、更通用的回退型问题，用于补充背景检索。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 回退型问题（用于补充语义背景）
    """
    logger.info(f"开始生成回退查询: {original_query}")
    if messages:
        step_back_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.STEP_BACK_QUERY_SYSTEM_PROMPT),
            ("human", query_transform_prompts.STEP_BACK_QUERY_PROMPT)
        ])
    else:
        step_back_prompt = PromptTemplate.from_template(query_transform_prompts.STEP_BACK_QUERY_PROMPT)
    step_back_chain = step_back_prompt | model

    try:
        response = await step_back_chain.ainvoke({"original_query": original_query,"messages": messages})
        step_back_query = response.content.strip()
        logger.info(f"回退查询生成成功: {step_back_query}")
        return step_back_query
    except Exception as e:
        logger.error(f"回退问题生成失败: {e}")
        return original_query



async def standardize_terminology(original_query, messages:List[AnyMessage]=None):
    """
    将用户的口语化表达转换为知识库标准术语。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 标准化术语后的问题
    """
    logger.info(f"开始术语标准化: {original_query}")
    if messages:
        standardize_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.STANDARDIZE_TERMINOLOGY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
            ("human", query_transform_prompts.STANDARDIZE_TERMINOLOGY_PROMPT)
        ]).partial(messages=messages)
    else:
        standardize_prompt = PromptTemplate.from_template(query_transform_prompts.STANDARDIZE_TERMINOLOGY_PROMPT)
    standardize_chain = standardize_prompt | model

    try:
        response = await standardize_chain.ainvoke({"original_query": original_query})
        standardized_query = response.content.strip()
        logger.info(f"术语标准化成功: {standardized_query}")
        return standardized_query
    except Exception as e:
        logger.error(f"术语标准化失败: {e}")
        return original_query


async def expand_implicit_query(original_query, messages:List[AnyMessage]=None):
    """
    展开用户隐含的完整问题意图，将简短问题扩展为完整表述。

    Args:
        original_query (str): 用户原始提问
        messages (List[AnyMessage]): 对话历史消息

    Returns:
        str: 展开后的完整问题
    """
    logger.info(f"开始展开隐含查询: {original_query}")
    if messages:
        expand_prompt = ChatPromptTemplate.from_messages([
            ("system", query_transform_prompts.EXPAND_IMPLICIT_QUERY_SYSTEM_PROMPT),
            ("placeholder", "{messages}"),
            ("human", query_transform_prompts.EXPAND_IMPLICIT_QUERY_PROMPT)
        ]).partial(messages=messages)
    else:
        expand_prompt = PromptTemplate.from_template(query_transform_prompts.EXPAND_IMPLICIT_QUERY_PROMPT)
    expand_chain = expand_prompt | model

    try:
        response = await expand_chain.ainvoke({"original_query": original_query})
        expanded_query = response.content.strip()
        logger.info(f"隐含查询展开成功: {expanded_query}")
        return expanded_query
    except Exception as e:
        logger.error(f"隐含查询展开失败: {e}")
        return original_query


async def decompose_to_components(original_query):
    """
    将询问具体物品的问题分解为其关键组成部分，以匹配知识库中的相关规定。

    适用场景：用户询问具体物品（如感应灯、智能手表等），但知识库中没有该物品的直接规定，
    而是对其关键组成部分（如锂电池、电子元件等）有相关规定。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 分解为组件后的问题
    """
    logger.info(f"开始组件分解改写: {original_query}")
    decompose_prompt = PromptTemplate.from_template(query_transform_prompts.COMPONENT_DECOMPOSE_PROMPT)
    decompose_chain = decompose_prompt | model

    try:
        response = await decompose_chain.ainvoke({"original_query": original_query})
        decomposed_query = response.content.strip()
        logger.info(f"组件分解改写成功: {decomposed_query}")
        return decomposed_query
    except Exception as e:
        logger.error(f"组件分解改写失败: {e}")
        return original_query


async def professional_prejudgment_rewrite(original_query):
    """
    基于专业知识对用户问题进行预判性改写，像资深客服一样直接定位到关键限制条件。

    适用场景：用户询问具体商品时，基于电商行业专业知识，直接预判该商品的关键限制因素，
    并将问题改写为包含具体限制条件的专业问题。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 基于专业预判改写后的问题
    """
    logger.info(f"开始专业预判改写: {original_query}")
    prejudgment_prompt = PromptTemplate.from_template(query_transform_prompts.PROFESSIONAL_PREJUDGMENT_PROMPT)
    prejudgment_chain = prejudgment_prompt | model

    try:
        response = await prejudgment_chain.ainvoke({"original_query": original_query})
        prejudged_query = response.content.strip()
        logger.info(f"专业预判改写成功: {prejudged_query}")
        return prejudged_query
    except Exception as e:
        logger.error(f"专业预判改写失败: {e}")
        return original_query


async def specification_prefill_rewrite(original_query):
    """
    为涉及规格限制的物品问题预填常见的限制条件。

    适用场景：用户询问的物品通常有明确的规格限制（如容量、重量、尺寸等），
    直接在问题中补充最常见的限制条件，提高匹配精度。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 预填规格限制后的问题
    """
    logger.info(f"开始规格预填改写: {original_query}")
    specification_prompt = PromptTemplate.from_template(query_transform_prompts.SPECIFICATION_PREFILL_PROMPT)
    specification_chain = specification_prompt | model

    try:
        response = await specification_chain.ainvoke({"original_query": original_query})
        prefilled_query = response.content.strip()
        logger.info(f"规格预填改写成功: {prefilled_query}")
        return prefilled_query
    except Exception as e:
        logger.error(f"规格预填改写失败: {e}")
        return original_query


async def scenario_refinement_rewrite(original_query):
    """
    根据物品特性将问题细分为最可能的具体使用场景。

    适用场景：用户询问的物品在不同场景下有不同规定，
    基于常见情况将问题细化为最可能的具体场景。

    Args:
        original_query (str): 用户原始提问

    Returns:
        str: 场景细分后的问题
    """
    logger.info(f"开始场景细分改写: {original_query}")
    scenario_prompt = PromptTemplate.from_template(query_transform_prompts.SCENARIO_REFINEMENT_PROMPT)
    scenario_chain = scenario_prompt | model

    try:
        response = await scenario_chain.ainvoke({"original_query": original_query})
        refined_query = response.content.strip()
        logger.info(f"场景细分改写成功: {refined_query}")
        return refined_query
    except Exception as e:
        logger.error(f"场景细分改写失败: {e}")
        return original_query


async def comprehensive_query_transform(original_query, strategies=None, messages: List[AnyMessage] = None):
    """
    电商综合查询变换函数，根据策略对用户购物/订单问题进行多维度改写。

    Args:
        original_query (str): 用户原始提问
        strategies (list): 变换策略列表，可选值：
            - 'rewrite': 基础意图重写
            - 'order_rewrite': 订单与物流查询重写（替代原 flight_rewrite）
            - 'product_rewrite': 商品参数与对比重写
            - 'step_back': 抽象意图回退
            - ...等
        messages (List[AnyMessage]): 对话历史消息
    """
    # 1. 更新默认策略列表：移除 flight_rewrite，加入 order_rewrite
    if strategies is None:
        strategies = [
            'rewrite',
            'order_rewrite',  # 电商核心：订单/物流重写
            'step_back',
            'standardize',
            'expand',
            'decompose',
            'professional',
            'specification',
            'scenario'
        ]

    logger.info(f"开始电商查询变换: {original_query}, 策略: {strategies}")

    results = original_query

    try:
        # 基础通用重写
        if 'rewrite' in strategies:
            results = await rewrite_query(original_query, messages)

        # 2. 修改：将 flight_rewrite 替换为 order_rewrite
        # 该函数需要你单独定义（见下方补充）
        if 'order_rewrite' in strategies:
            # 假设这个函数由于 LLM 报错返回了 None
            transformed = await order_rewrite_query(original_query, messages)
            if transformed:
                results = transformed

        # # 3. 可选：增加商品搜索重写 (针对 SKU/属性)
        # if 'product_rewrite' in strategies:
        #     results = await product_rewrite_query(original_query, messages)

        # 保持其他策略逻辑不变（它们通常是通用的 LLM 改写）
        if 'step_back' in strategies:
            results = await generate_step_back_query(original_query, messages)

        if 'standardize' in strategies:
            results = await standardize_terminology(original_query, messages)

        # ... 后续逻辑保持一致 ...
        if 'decompose' in strategies:
            results = await decompose_to_components(original_query)

        if 'professional' in strategies:
            results = await professional_prejudgment_rewrite(original_query)

        if 'specification' in strategies:
            results = await specification_prefill_rewrite(original_query)

        if 'scenario' in strategies:
            results = await scenario_refinement_rewrite(original_query)

        logger.info(f"电商查询变换完成: {results}")
        return results

    except Exception as e:
        logger.error(f"综合查询变换失败: {e}")
        return results

async def order_rewrite_query(original_query: str, messages: List[AnyMessage]) -> str:
    """
    专门针对订单/物流场景的重写器。
    逻辑：从对话历史中抓取订单号、快递单号或商品指代，改写为包含具体实体的完整查询。
    """
    logger.info(f"开始订单物流查询重写: {original_query}")
    order_rewrite_prompt = ChatPromptTemplate.from_messages([
        ("system", query_transform_prompts.ORDER_QUERY_REWRITE_SYSTEM_PROMPT),
        ("human", query_transform_prompts.ORDER_QUERY_REWRITE_PROMPT)
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    order_rewriter = order_rewrite_prompt | model

    try:
        response = await order_rewriter.ainvoke({"original_query": original_query, "messages": messages})
        rewritten = response.content.strip()
        logger.info(f"订单物流查询重写成功: {rewritten}")
        return rewritten
    except Exception as e:
        logger.error(f"订单物流查询重写失败: {e}")
        return original_query
