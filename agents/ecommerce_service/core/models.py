"""
共享的模型实例定义
避免循环导入问题
"""
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from config.utils import config_manager

# 从配置文件获取模型配置
llm_model_config = config_manager.get_agents_config().get("llm", {})
emb_model_config = config_manager.get_agents_config().get("embedding", {})



# 创建共用模型实
if llm_model_config.get("enable_thinking"):
    content_model = ChatOpenAI(
        model_name=llm_model_config.get("model"),
        temperature=llm_model_config.get("temperature", 0.7),
        extra_body={"thinking":{"type":"enabled"}},
        streaming=True,
        openai_api_key=llm_model_config.get("api_key"),
        openai_api_base=llm_model_config.get("base_url")
    )
else:
    content_model = ChatOpenAI(
        model_name=llm_model_config.get("model"),
        temperature=llm_model_config.get("temperature", 0.7),
        openai_api_key=llm_model_config.get("api_key"),
        openai_api_base=llm_model_config.get("base_url")
    )


base_model = ChatOpenAI(
    model_name=llm_model_config.get("model"),
    temperature=llm_model_config.get("temperature", 0.7),
    openai_api_key=llm_model_config.get("api_key"),
    openai_api_base=llm_model_config.get("base_url")
)
structed_model = ChatOpenAI(
    model_name=llm_model_config.get("router_model"),
    temperature=llm_model_config.get("router_temperature", 0.7),
    openai_api_key=llm_model_config.get("router_api_key"),
    openai_api_base=llm_model_config.get("router_base_url"),
    streaming=False
)


image_model = ChatOpenAI(
    model_name=llm_model_config.get("image_thinking_model"),
    temperature=llm_model_config.get("image_thinking_temperature", 0.7),
    openai_api_key=llm_model_config.get("image_thinking_api_key"),
    openai_api_base=llm_model_config.get("image_thinking_base_url")
)


emb_model = OpenAIEmbeddings(
    model=emb_model_config.get("embedding_model"),
    openai_api_key=emb_model_config.get("api_key"),
    openai_api_base=emb_model_config.get("base_url"),
    # ！！！核心修复：必须加上这一行！！！
    chunk_size=10,

    # 建议：如果你使用的是 text-embedding-v4，建议把下面这行注释取消掉，
    # 这样能确保生成的向量维度是你 .env 里设置的 1024，防止和数据库不匹配。
    dimensions=emb_model_config.get("dimensions"),
        # =========== 新增的核心修复 ===========
    # 3. 禁用 Embedding 上下文长度检查（防止它去计算 Token）
    check_embedding_ctx_length=False,

    # 4. 彻底禁用 tiktoken（禁止将文本转换为 Token ID 发送）
    tiktoken_enabled=False
)
