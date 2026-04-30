import chromadb

# 1. 初始化ChromaDB客户端（适配你的服务端模式）
# 从你的输出看，ChromaDB是HTTP服务端模式，无需指定path
client = chromadb.HttpClient(host="119.91.69.62", port=8000)

# 2. 查看数据库中所有的集合
print("=== 数据库中所有集合 ===")
collections = client.list_collections()
for coll in collections:
    print(f"集合名称: {coll.name}, 数据条数: {coll.count()}")

# 3. 查看指定集合的详细数据（使用实际存在的conversation_memory）
target_collection_name = "conversation_memory"

try:
    # 获取目标集合
    collection = client.get_collection(name=target_collection_name)

    # 3.1 查看集合基本信息
    print(f"\n=== 集合 {target_collection_name} 基本信息 ===")
    print(f"数据总条数: {collection.count()}")
    print(f"集合元数据: {collection.metadata}")

    # 3.2 查看所有数据（关键修复：去掉include中的ids）
    print(f"\n=== 集合 {target_collection_name} 所有数据 ===")
    all_data = collection.get(
        limit=collection.count(),  # 动态获取总条数
        offset=0,
        # 核心修复：include中移除ids（ids默认返回，无需指定）
        include=["metadatas", "documents", "embeddings"]
    )

    # 遍历打印每条数据（ids是默认返回的，直接读取即可）
    for idx, (id_, doc, meta, embedding) in enumerate(
        zip(all_data["ids"], all_data["documents"], all_data["metadatas"], all_data["embeddings"], strict=False)
    ):
        print(f"\n【第{idx+1}条数据】")
        print(f"ID: {id_}")
        # 处理空文档/元数据的情况（避免报错）
        print(f"文档内容: {doc[:200]}..." if (doc and len(doc) > 200) else f"文档内容: {doc}")
        print(f"元数据: {meta}")
        # 处理空向量的情况
        if embedding:
            print(f"嵌入向量（前5维）: {embedding[:5]}, 向量维度: {len(embedding)}")
        else:
            print("嵌入向量: 无")

except Exception as e:
    print(f"\n错误详情：{type(e).__name__} - {e}")
    print(f"确认集合是否存在：{[coll.name for coll in client.list_collections()]}")
