import asyncio
from typing import List, Dict, Any, Optional, Union

import pandas as pd
from common.logging import get_logger
from .interfaces import AsyncLLMProvider, AsyncVectorStore, AsyncDBConnector, AsyncEmbeddingProvider
import time
from datetime import datetime, date
from decimal import Decimal

# 获取日志记录器
logger = get_logger("text2sql.base")

class AsyncSmartSqlBase:
    """异步Text2SQL基础类"""
    
    def __init__(self, 
                 llm_provider: Optional[AsyncLLMProvider] = None,
                 embedding_provider: Optional[AsyncEmbeddingProvider] = None,
                 vector_store: Optional[AsyncVectorStore] = None,
                 db_connector: Optional[AsyncDBConnector] = None,
                 config: Dict[str, Any] = None):
        
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.db_connector = db_connector
        self.config = config or {}
        self.dialect = self.config.get("dialect", "SQL")
        self.language = self.config.get("language", None)
        self.max_tokens = self.config.get("llm", {}).get("max_tokens", 20000)
        
        logger.info(f"初始化AsyncSmartSqlBase，配置信息：dialect={self.dialect}, language={self.language}, max_tokens={self.max_tokens}")
    
    async def initialize(self) -> None:
        """异步初始化组件"""
        logger.info("开始初始化AsyncSmartSqlBase组件")
        # 创建连接池和初始化其他资源
        if self.db_connector:
            await self.db_connector.connect()
        if self.vector_store:
            await self.vector_store.initialize()
        logger.info("AsyncSmartSqlBase组件初始化完成")
    
    async def shutdown(self) -> None:
        """异步关闭资源"""
        logger.info("开始关闭AsyncSmartSqlBase资源")
        if self.db_connector:
            await self.db_connector.close()
        logger.info("AsyncSmartSqlBase资源关闭完成")
    
    async def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """使用嵌入提供者生成嵌入向量"""
        if not self.embedding_provider:
            raise ValueError("未配置嵌入提供者，无法生成嵌入向量")
        res = await self.embedding_provider.generate_embedding(data, **kwargs)
        return res["embedding"]
    
    async def generate_sql(self, question: str, user_id: str, allow_llm_to_see_data=False, **kwargs) -> str:
        """异步生成SQL查询"""
        logger.info(f"开始生成SQL，问题：{question}")
        logger.info(f"generate_sql+DEBUG的用户id: {user_id}")
        try:
            # 并行获取相关信息
            logger.debug("并行获取相关信息")
            question_sql_task = self.vector_store.get_similar_question_sql(question, **kwargs)
            ddl_task = self.vector_store.get_related_ddl(question, **kwargs)
            doc_task = self.vector_store.get_related_documentation(question, **kwargs)
            
            # 等待所有异步任务完成
            question_sql_list, ddl_list, doc_list = await asyncio.gather(
                question_sql_task, ddl_task, doc_task
            )
            
            # 构建提示
            # logger.debug("构建SQL提示") 
            prompt = await self._get_sql_prompt(
                question=question,
                question_sql_list=question_sql_list,
                ddl_list=ddl_list,
                doc_list=doc_list,
                user_id=user_id,
                **kwargs
            )
            logger.info(f"构建SQL提示结束: {prompt}")
            # 调用异步LLM
            logger.info("调用LLM生成回答")
            llm_response = await self.llm_provider.submit_prompt(prompt, **kwargs)
            logger.info(f"LLM回答: {llm_response}")
            
            # 处理中间SQL(如果需要数据库内省)
            if 'intermediate_sql' in llm_response and allow_llm_to_see_data:
                intermediate_sql = await self._extract_sql(llm_response)
                logger.info(f"执行中间SQL进行数据探索: {intermediate_sql}")
                try:
                    result = await self.db_connector.run_sql(intermediate_sql)
                    if isinstance(result, dict) and result.get('error'):
                        # 处理错误情况
                        error_msg = result.get('message', '未知错误')
                        logger.error(f"执行中间SQL失败: {error_msg}")
                        result =  f"运行 intermediate SQL出错: {error_msg}"

                    # 确认是DataFrame后再使用
                    df = result
                    if isinstance(df, pd.DataFrame):
                        updated_doc_list = doc_list + [
                            f"下面是intermediate SQL查询结果: \n" + df.to_markdown()
                        ]
                    else:
                        updated_doc_list = doc_list + [
                            f"下面是intermediate SQL查询结果: \n" + df
                        ]

                    prompt = await self._get_sql_prompt(
                        question=question,
                        question_sql_list=question_sql_list,
                        ddl_list=ddl_list,
                        doc_list=updated_doc_list,
                        **kwargs
                    )
                    llm_response = await self.llm_provider.submit_prompt(prompt, **kwargs)
                except Exception as e:
                    logger.error(f"执行中间SQL失败: {str(e)}")
                    return f"Error running intermediate SQL: {e}"
            
            # 异步提取最终SQL
            sql = await self._extract_sql(llm_response)
            logger.info(f"提取的最终SQL: {sql}")
            
            # 返回生成的SQL
            return sql,ddl_list
        except Exception as e:
            # 异步处理异常
            logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
            for plugin in getattr(self, 'plugins', []):
                await plugin.on_error(e, question=question, **kwargs)
            raise
    
    # async def _get_sql_prompt(self, question, question_sql_list, ddl_list, doc_list, **kwargs):
    #     """构建SQL生成的提示信息"""
        
    #     # 1. 准备模板变量
    #     dialect = self.dialect
    #     database_context = self._build_database_context(ddl_list)
    #     descriptions = self._build_descriptions(doc_list)
        
    #     # 2. 获取或构建系统提示模板
    #     system_prompt_template = self._get_system_prompt_template()
        
    #     # 3. 填充系统提示
    #     system_prompt = system_prompt_template.format(
    #         dialect=dialect,
    #         database_context=database_context,
    #         descriptions=descriptions,
    #         # 注入当前北京时间，确保 SQL 生成时能处理“最近一小时”、“昨天”等逻辑
    #         time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
    #         **kwargs # 如果后续还有其他动态参数也能透传
    #     )
        
    #     # 4. 构建消息列表
    #     messages = [{"role": "system", "content": system_prompt}]
        
    #     # 5. 添加示例问答对
    #     for example in question_sql_list:
    #         if isinstance(example, dict) and "question" in example and "sql" in example:
    #             messages.append({"role": "user", "content": example["question"]})
    #             messages.append({"role": "assistant", "content": example["sql"]})
        
    #     # 6. 添加当前问题
    #     messages.append({"role": "user", "content": question})
        
    #     return messages
    async def _get_sql_prompt(self, question,user_id: str, question_sql_list, ddl_list, doc_list, **kwargs,):
        """构建SQL生成的提示信息 (已修复：注入实时Schema)"""
        
        # 1. 动态获取实时数据库 Schema (这是修复的核心！)
        live_schema_info = ""
        if self.db_connector:
            try:
                # 调用 Connector 的 get_schema 方法
                live_schema_info = await self.db_connector.get_schema()
                logger.info(f"成功获取实时 Schema，长度: {len(live_schema_info)}")
            except Exception as e:
                logger.error(f"动态获取 Schema 失败: {e}")
                live_schema_info = "Schema获取失败，请根据常识推断。"

        # 2. 准备模板变量 (将实时 Schema 传入构建函数)
        dialect = self.dialect
        database_context = self._build_database_context(ddl_list, live_schema_info)
        descriptions = self._build_descriptions(doc_list)
        # 3. 获取或构建系统提示模板
        system_prompt_template = self._get_system_prompt_template()
        logger.warning(user_id+'-----------------------------------------------------------------')
        # 4. 填充系统提示
        system_prompt = system_prompt_template.format(
            dialect=dialect,
            database_context=database_context,
            descriptions=descriptions,
            user_id=user_id,
            # 注入当前北京时间
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            **kwargs
        )
        
        # 5. 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 6. 添加示例问答对
        for example in question_sql_list:
            if isinstance(example, dict) and "question" in example and "sql" in example:
                messages.append({"role": "user", "content": example["question"]})
                messages.append({"role": "assistant", "content": example["sql"]})
        
        # 7. 添加当前问题
        messages.append({"role": "user", "content": question})
        
        return messages

    def _get_system_prompt_template(self):
        """获取系统提示模板"""
        # 优先使用配置中的自定义提示
        custom_prompt = self.config.get("initial_prompt", None)
        if custom_prompt:
            return custom_prompt
        
#         # 基于Anthropic最佳实践的系统提示模板
#         template = """<role>
# 你是一个专业的 {dialect} 数据库查询专家，擅长将自然语言问题准确转换为 SQL 查询。
# </role>

# <task>
# 根据用户的自然语言问题，结合提供的数据库上下文和业务描述，生成一个精确、高效的 SQL 查询。
# </task>

# <context>
# {database_context}

# {descriptions}

# <sql_dialect>{dialect}</sql_dialect>
# </context>

# <constraints>
# 1. 严格使用提供的数据库上下文中的表名和列名，不要创造不存在的元素
# 2. 只能生成查询语句，不能生成插入、更新、删除语句
# 2. 确保 SQL 语法符合指定的 {dialect} 方言规范
# 3. 优先选择查询所需的最少列，避免不必要的 SELECT *
# 4. 生成的查询必须是单一的、完整的、可执行的 SQL 语句
# 5. 充分利用提供的示例和历史对话信息
# 6. 确保查询逻辑准确反映用户的真实意图
# 7. 如果用户查询具体的航班号，生成的 sql 中除了把航班号作为条件外，还需要把航班号作为查询字段。
# 8. 如果用户当前提供的信息不足以生成SQL，一定不要强行生成SQL（特别不能生成查询所有航班明细的 sql）。而是返回空字符串。
# </constraints>

# <output_format>
# 直接输出生成的 SQL 查询语句，不包含任何解释、注释或其他文本。

# 示例输出格式：
# SELECT column1, column2 FROM table_name WHERE condition;
# </output_format>

# <reasoning_steps>
# 在生成 SQL 之前，请按以下步骤思考：

# 1. **问题分析**: 理解用户问题的核心意图和所需信息
# 2. **表结构映射**: 确定需要查询的表和相关字段
# 3. **关系识别**: 识别表之间的关联关系（如需要JOIN）
# 4. **条件提取**: 从问题中提取筛选条件和约束
# 5. **聚合需求**: 判断是否需要聚合函数（COUNT、SUM等）
# 6. **查询构建**: 按照SQL语法规范构建查询语句
# 7. **优化检查**: 确保查询效率和准确性
# </reasoning_steps>

# 现在，请根据用户的问题生成相应的 SQL 查询："""
        
#         return template
  # 基于电商业务逻辑优化的模板
        template = """<role>
你是一个专业的 {dialect} 数据库查询专家，擅长将电商业务的自然语言问题准确转换为高效的 SQL 查询。
</role>

<task>
根据用户的自然语言问题，结合提供的电商数据库上下文（订单、商品、库存、物流），生成一个精确、高效的 SQL 查询。
</task>

<context>
{database_context}
<current_user_info>
当前用户的 User ID: {user_id}
注意：当用户在问题中提到“我的”、“咱们”、“本账号”时，必须使用此 ID 进行过滤。
</current_user_info>
{descriptions}

<sql_dialect>{dialect}</sql_dialect>
</context>

<constraints>
1. 严格使用提供的数据库上下文中的表名和列名，不要创造不存在的元素。
2. 只能生成查询（SELECT）语句，严禁生成 INSERT、UPDATE、DELETE 或 DROP 语句。
3. 确保 SQL 语法符合指定的 {dialect} 方言规范。
4. 优先选择查询所需的最少列，避免使用 SELECT *，除非用户明确要求查看“所有详情”。
5. 充分利用提供的示例和历史对话信息，处理指代消解（如“它”、“这个订单”）。
6. **实体对齐**：如果用户查询具体的订单号(order_id)、物流单号(tracking_number)或商品编码(sku_id)，生成的 SQL 中除了将其作为 WHERE 条件外，**必须**将该 ID 作为查询字段返回，以便前端组件进行数据校验和渲染。
7. **防御性编程**：如果用户当前提供的信息不足以生成有效的过滤条件，**严禁生成查询全表数据的 SQL**（例如：严禁生成不带 WHERE 条件的 SELECT * FROM orders）。
8. **空结果处理**：如果信息严重不足（例如用户只说“查一下”但未指明查什么），请返回空字符串，不要尝试猜测意图。
9. **时间范围**：对于“最近的订单”、“上个月的支出”等描述，请结合当前时间 {time} 生成准确的时间区间过滤条件。
10. **别名规则**：如果使用表别名（Alias），必须保证 SELECT 子句和 JOIN 子句中的别名完全一致！
   - 错误示例：SELECT t1.name FROM table t2
   - 正确示例：SELECT t1.name FROM table t1
11. 为了防止错误，**建议直接使用全表名**，或者使用极简别名（如 t1, t2）。
12. 实体对齐：查询 order_id 时必须同时返回该字段。
</constraints>

<output_format>
直接输出生成的 SQL 查询语句，不包含任何解释、注释或其他文本。

示例输出格式：
SELECT order_id, status, total_amount FROM orders WHERE order_id = '12345678';
</output_format>

<reasoning_steps>
在生成 SQL 之前，请按以下步骤思考：
1. **意图分析**: 用户是想查物流、查订单价格、还是查商品库存？
2. **关键实体提取**: 提取订单 ID、SKU ID、时间区间等核心过滤因子。
3. **关联路径**: 如果涉及商品名称和订单状态，是否需要 JOIN 订单表和商品表？
4. **安全检查**: 该查询是否包含 WHERE 条件？是否会造成数据库性能负载？
5. **构建与优化**: 按照 SQL 语法构建，并确保字段名完全匹配 Schema。
</reasoning_steps>

现在，请根据用户的问题生成相应的 SQL 查询："""
        return template
    
    # def _build_database_context(self, ddl_list):
    #     """构建数据库上下文信息"""
    #     if not ddl_list:
    #         return "<database_schema>\n暂无数据库架构信息\n</database_schema>"
        
    #     ddl_content = ""
    #     for ddl in ddl_list:
    #         if isinstance(ddl, dict) and "ddl" in ddl and "description" in ddl:
    #             # 新格式：包含description和ddl
    #             ddl_content += f"""<table_info>
    #                             <description>{ddl['description']}</description>
    #                             <ddl>{ddl['ddl']}</ddl>
    #                             </table_info>

    #                             """
    #         else:
    #             # 兼容旧格式
    #             ddl_content += f"""<table_info>
    #                                     <ddl>{ddl}</ddl>
    #                                 </table_info>

    #                                 """
        
    #     # 检查token限制
    #     if self._estimate_tokens(ddl_content) > self.max_tokens * 0.4:  # 最多占用40%的token
    #         logger.warning("DDL内容过长，将被截断")
    #         ddl_content = ddl_content[:int(self.max_tokens * 0.4 * 2)]  # 简单截断
    #         ddl_content += "\n<!-- 内容因长度限制被截断 -->"
        
    #     return f"""<database_schema>{ddl_content.strip()}</database_schema>"""
    
    def _build_database_context(self, ddl_list, live_schema_info=""):
        """构建数据库上下文信息 (已修复：优先使用实时 Schema)"""
        
        content = ""
        
        # 1. 优先放入实时的全库 Schema
        if live_schema_info:
            content += f"""
<full_database_schema>
{live_schema_info}
</full_database_schema>
"""

        # 2. 补充检索到的 DDL (如果有)
        if ddl_list:
            ddl_content = ""
            for ddl in ddl_list:
                if isinstance(ddl, dict) and "ddl" in ddl:
                    desc = ddl.get('description', '')
                    ddl_content += f"Table Info: {desc}\nDDL: {ddl['ddl']}\n\n"
                else:
                    ddl_content += f"DDL: {ddl}\n\n"
            
            if ddl_content:
                content += f"""
<related_ddl_snippets>
{ddl_content}
</related_ddl_snippets>
"""

        if not content:
            return "<database_schema>\n暂无数据库架构信息，请仔细检查数据库连接。\n</database_schema>"
        
        # 检查token限制 (简单截断防止溢出)
        if self._estimate_tokens(content) > self.max_tokens * 0.6:
            logger.warning("Schema内容过长，正在截断...")
            content = content[:int(self.max_tokens * 0.6 * 2)]
            content += "\n<!-- Schema truncated -->"
        
        return f"""<database_schema>{content}</database_schema>"""
    def _build_descriptions(self, doc_list):
        """构建描述信息"""
        if not doc_list:
            return "<business_context>\n暂无业务上下文信息\n</business_context>"
        
        doc_content = ""
        for i, doc in enumerate(doc_list, 1):
            doc_content += f"""<context_item id="{i}">{doc}</context_item>"""
        
        # 检查token限制
        if self._estimate_tokens(doc_content) > self.max_tokens * 0.3:  # 最多占用30%的token
            logger.warning("文档内容过长，将被截断")
            doc_content = doc_content[:int(self.max_tokens * 0.3 * 2)]  # 简单截断
            doc_content += "\n<!-- 内容因长度限制被截断 -->"
        
        return f"""<business_context>{doc_content.strip()}</business_context>"""
    
    async def _extract_sql(self, llm_response):
        """异步从LLM响应中提取SQL"""
        import re
        
        # 处理不同格式的LLM响应
        if isinstance(llm_response, dict) and "content" in llm_response:
            llm_response_text = llm_response["content"]
        elif isinstance(llm_response, str):
            llm_response_text = llm_response
        else:
            logger.warning(f"无法识别的LLM响应格式: {type(llm_response)}")
            return llm_response  # 返回原始响应
        # 尝试各种模式提取SQL
        # 1. WITH CTE模式
        sqls = re.findall(r"\bWITH\b .*?;", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug(f"从WITH CTE模式提取SQL: {sqls[-1]}")
            return sqls[-1]
        
        # 2. SELECT语句
        sqls = re.findall(r"SELECT.*?;", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug(f"从SELECT语句提取SQL: {sqls[-1]}")
            return sqls[-1]
        
        # 3. 代码块(带SQL标签)
        sqls = re.findall(r"```sql\n(.*?)```", llm_response_text, re.DOTALL | re.IGNORECASE)
        if sqls:
            logger.debug("从SQL代码块提取SQL")
            return sqls[-1].strip()
        
        # 4. 一般代码块
        sqls = re.findall(r"```(.*?)```", llm_response_text, re.DOTALL)
        if sqls:
            logger.debug("从一般代码块提取SQL")
            return sqls[-1].strip()
        
        # 5. 如果没有匹配，返回原始响应
        logger.warning("无法从LLM响应中提取SQL，返回原始响应")
        return llm_response
    
    async def run_sql(self, sql: str, **kwargs):
        """异步执行SQL查询"""
        result = await self.db_connector.run_sql(sql, **kwargs)
        return serialize_result(result)

    def _estimate_tokens(self, text):
        """估算文本的token数量"""
        return len(text) / 2  # 简单估算
    
    def split_data(self, text):
        """分割数据"""
        tmp = []
        for item in text:
            if self._estimate_tokens(str(item))+self._estimate_tokens(str(tmp)) > self.max_tokens:
                break
            tmp.append(item)
        return tmp.copy()

    async def ask(self, question: str,user_id: str, **kwargs) -> Dict[str, Any]:
        try:
            logger.info(f"ask+DEBUG的用户id: {user_id}")
# 使用generate_sql获取SQL
            # 注意：这里的 sql 可能是字符串，也可能是包含错误信息的字典
            raw_response, ddl_list = await self.generate_sql(question=question, user_id=user_id, **kwargs)
            
            # --- 【新增修复逻辑开始】 ---
            final_sql = ""
            
            # 1. 类型清洗：从字典中提取内容，或者直接使用字符串
            if isinstance(raw_response, dict):
                # 如果是字典，尝试提取 content，如果提取不到则为空
                final_sql = raw_response.get('content', '')
            elif isinstance(raw_response, str):
                final_sql = raw_response
            
            # 2. 有效性检查：判断是否是真正的 SQL
            # 如果是空字符串、None、或者 LLM 回复了 "空字符串"（根据之前的日志），则视为无效
            is_valid_sql = False
            if final_sql and isinstance(final_sql, str):
                cleaned_sql = final_sql.strip()
                if cleaned_sql and cleaned_sql != '空字符串':
                    is_valid_sql = True
                    final_sql = cleaned_sql  # 更新为去除空格后的版本
            # --- 【新增修复逻辑结束】 ---

            sql_result = {
                'sql': final_sql,  # 这里存入清洗后的字符串，前端展示更友好
                'ddl': ddl_list,
                'data': None,
                'error': None
            }
            
            # 3. 根据检查结果决定是否执行数据库查询
            if is_valid_sql:
                try:
                    # 执行SQL (确保传进去的是字符串 final_sql)
                    result = await self.db_connector.run_sql(final_sql)
                    result = serialize_result(result)
                except Exception as db_err:
                    # 捕获 SQL 执行层面的错误（如语法错误）
                    logger.warning(f"SQL执行出错: {db_err}")
                    result = {'error': str(db_err)}
            else:
                # 如果没有生成有效 SQL，直接返回空结果，避免报错
                logger.info(f"未生成有效SQL，跳过数据库查询。原始内容类型: {type(raw_response)}")
                result = []

            # 4. 后续处理保持不变
            if self._estimate_tokens(str(result)) > self.max_tokens:
                sql_result['data'] = self.split_data(result)
                return sql_result
            
            # 检查SQL执行结果
            if isinstance(result, dict) and result.get('error'):
                sql_result['data'] = result
            else:
                # 在这里应用序列化函数
                sql_result['data'] = result
            return sql_result

        except Exception as e:
            logger.error(f"问答处理失败: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'sql': None,
                'ddl': None,
                'data': None,
            }

    async def train(
        self,
        training_data: Union[Dict[str, Any], List[Dict[str, Any]]] = None,
        mode: str = "incremental",  # 差异化训练模式
        source: str = "user",      # 标记训练数据来源
        feedback_data: Dict[str, Any] = None,  # 用户反馈数据
        **kwargs
    ) -> Dict[str, Any]:
        """增强的异步训练接口
        Args:
            training_data: 单条或多条训练数据 
        Returns:
            训练结果信息
        """
        results = {'success': [], 'failed': [], 'status': 'completed'}
    
        # 确保training_data是列表
        if not isinstance(training_data, list):
            training_data = [training_data]
        
        for item in training_data:
            try:
                if 'documentation' in item:
                    doc_id = await self.vector_store.add_documentation(
                        item['documentation'], 
                        metadata={'source': source, 'timestamp': time.time()}
                    )
                    results['success'].append({'type': 'documentation', 'id': doc_id})
                    
                elif 'ddl' in item:
                    # 检查是否有描述字段，如果没有则使用DDL本身作为描述
                    description = item.get('description', item['ddl'])
                    ddl_id = await self.vector_store.add_ddl(
                        item['ddl'],
                        description=description
                    )
                    results['success'].append({'type': 'ddl', 'id': ddl_id})
                    
                elif 'question' in item and 'sql' in item:
                    # 保存问题-SQL对和向量嵌入
                    pair_id = await self.vector_store.add_question_sql(
                        question=item['question'],
                        sql=item['sql'],
                        metadata={
                            'source': source, 
                            'timestamp': time.time(),
                            'tags': item.get('tags', [])
                        }
                    )
                    results['success'].append({'type': 'question_sql', 'id': pair_id})
                    
                else:
                    results['failed'].append({
                        'item': item,
                        'reason': '未识别的训练数据类型'
                    })
            except Exception as e:
                logger.error(f"训练项目失败: {str(e)}", exc_info=True)
                results['failed'].append({
                    'item': item,
                    'reason': str(e)
                })
        
        return results


    def get_prompt_config_example(self):
        """获取 prompt 配置示例，帮助用户理解如何自定义 prompt"""
        example_config = {
            "initial_prompt": """<role>
你是一个专业的 {dialect} 数据库分析师，专门为业务用户提供数据查询服务。
</role>

<task>
根据业务问题生成准确的 SQL 查询，重点关注业务价值和数据洞察。
</task>

<context>
{database_context}
{descriptions}
<sql_dialect>{dialect}</sql_dialect>
</context>

<guidelines>
1. 优先理解业务需求背后的真实意图
2. 生成高效、可读性强的 SQL 查询
3. 确保数据准确性和查询性能
4. 尽量查出航班号字段信息。
4. 遵循企业数据安全和隐私规范
</guidelines>

<output_format>
输出格式：纯 SQL 查询语句
</output_format>

请根据用户问题生成相应的 SQL 查询：""",
            
            "dialect": "PostgreSQL",
            "language": "zh-CN",
            "llm": {
                "max_tokens": 20000,
                "temperature": 0.1,
                "model": "claude-3-sonnet"
            }
        }
        
        return example_config
    
    def validate_prompt_template(self, template: str) -> dict:
        """验证 prompt 模板的有效性"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "required_placeholders": ["{dialect}", "{database_context}", "{descriptions}"]
        }
        
        # 检查必需的占位符
        for placeholder in validation_result["required_placeholders"]:
            if placeholder not in template:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"缺少必需的占位符: {placeholder}")
        
        # 检查模板结构
        recommended_sections = ["<role>", "<task>", "<context>", "<output_format>"]
        missing_sections = [section for section in recommended_sections if section not in template]
        if missing_sections:
            validation_result["warnings"].append(f"建议添加以下结构化标签: {', '.join(missing_sections)}")
        
        # 检查模板长度
        if len(template) > 10000:
            validation_result["warnings"].append("模板过长，可能影响性能")
        elif len(template) < 100:
            validation_result["warnings"].append("模板过短，可能缺少必要信息")
        
        return validation_result

def serialize_result(obj):
    """
    递归处理结果对象，将不可序列化的类型转换为可序列化类型
    """
    if isinstance(obj, dict):
        return {k: serialize_result(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_result(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_result(item) for item in obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif pd.isna(obj):  # 处理NaN和None
        return None
    elif hasattr(obj, 'to_dict'):  # 处理Pandas DataFrame或Series
        return serialize_result(obj.to_dict(orient='records'))
    else:
        return obj
