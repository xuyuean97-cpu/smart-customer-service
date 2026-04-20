"""
知识库API客户端
提供与知识库系统异步通信功能
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from common.logging import get_logger


# 在 retrieval.py 的文件顶部，或者一个专门的 config/cache 文件中
_dataset_id_cache = {}

# 获取模块日志记录器
logger = get_logger("text2kb")
# async def get_dataset_id(address: str, name: str, api_key: str) -> str:
#     """
#     异步获取知识库数据集ID
    
#     Args:
#         address: API地址
#         name: 数据集名称
#         api_key: API密钥
        
#     Returns:
#         数据集ID字符串，如果获取失败则返回空字符串
#     """
#     logger.info(f"获取数据集ID: {name}")
#     # 构建API URL
#     base_url = f"http://{address}/api/v1/datasets"
#     # 设置查询参数
#     params = {
#         "page": 1,
#         "page_size": 10,
#         "orderby": "create_time",
#         "name": name
#     }
#     # 设置请求头
#     headers = {
#         "Authorization": f"Bearer {api_key}"
#     }
    
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(base_url, params=params, headers=headers) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     if data.get('data') and len(data['data']) > 0:
#                         dataset_id = data['data'][0]['id']
#                         logger.debug(f"成功获取数据集ID: {dataset_id} (数据集: {name})")
#                         return dataset_id
#                     logger.warning(f"数据集不存在: {name}")
#                 else:
#                     logger.warning(f"获取数据集ID API请求失败，状态码: {response.status}")
#                 return ""
#     except Exception as e:
#         logger.error(f"获取数据集ID异常: {e}", exc_info=True)
#         return ""
async def get_dataset_id(base_url, dataset_name, api_key):
    # --- 步骤 A: 先查缓存 ---
    if dataset_name in _dataset_id_cache:
        # print(f"DEBUG: 命中缓存! {dataset_name} -> {_dataset_id_cache[dataset_name]}")
        return _dataset_id_cache[dataset_name]

    # --- 步骤 B: 准备 URL ---
    # 1. 清理 base_url，确保没有 http/https 前缀，也没有尾部斜杠
    clean_base = base_url.replace("http://", "").replace("https://", "").rstrip("/")
    
    # 2. 拼接完整的 API 路径
    # RAGFlow 获取数据集列表的标准接口通常是 /api/v1/datasets/list 或者 /api/v1/datasets
    # 我们加上 http:// 前缀
    request_url = f"http://{clean_base}/api/v1/datasets"

    # --- 步骤 C: 准备请求参数 ---
    # page=1, page_size=100 确保能拉取到足够多的列表进行查找
    params = {
        "page": 1, 
        "page_size": 100, 
        "name": dataset_name # 部分版本的 API 支持直接按名字过滤
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}", 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json"
    }

    print(f"DEBUG: 正在向服务器获取ID... URL: {request_url}, Name: {dataset_name}")

    try:
        # trust_env=False 忽略系统代理，防止本地 VPN/代理导致连接失败
        async with aiohttp.ClientSession(trust_env=False) as session:
            async with session.get(request_url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # --- 步骤 D: 解析响应 (核心修复部分) ---
                    # 服务器返回结构示例: {'code': 0, 'data': [ {'id': '...', 'name': 'test'}, ... ]}
                    
                    found_id = None
                    if data.get('code') == 0 and 'data' in data:
                        dataset_list = data['data']
                        
                        # 情况1: data 是列表 (List) - 最常见的情况
                        if isinstance(dataset_list, list):
                            for item in dataset_list:
                                if item.get('name') == dataset_name:
                                    found_id = item.get('id')
                                    break
                        
                        # 情况2: data 是字典 (Dict) - 兼容某些特殊 API 返回
                        elif isinstance(dataset_list, dict):
                            if dataset_list.get('name') == dataset_name:
                                found_id = dataset_list.get('id')
                    
                    # --- 步骤 E: 处理结果 ---
                    if found_id:
                        print(f"DEBUG: 成功解析并缓存数据集ID: {dataset_name} -> {found_id}")
                        _dataset_id_cache[dataset_name] = found_id
                        return found_id
                    else:
                        print(f"ERROR: 未找到名为 '{dataset_name}' 的数据集. API响应: {data}")
                        return None

                else:
                    text = await response.text()
                    print(f"ERROR: 获取数据集ID请求失败. 状态码: {response.status}, 响应: {text}")
                    return None

    except Exception as e:
        print(f"ERROR: 获取数据集ID发生网络异常: {e}")
        return None

async def retrieve_from_kb(question: str
                           , dataset_name: str
                           , address: str = None
                           , api_key: str = None
                           , similarity_threshold: float = 0.2
                           ,vector_similarity_weight:float=0.5
                           , top_k: int =5
                           ,key_words:bool=True) -> List[Dict[str, Any]]:
    """
    从知识库中检索信息
    
    Args:
        question: 问题文本
        dataset_name: 数据集名称
        address: API地址，默认从配置中获取
        api_key: API密钥，默认从配置中获取
        similarity_threshold: 相似度阈值，低于此值的结果将被标记，默认为0.1
        top_k: 检索结果数量上限，默认为10
        
    Returns:
        检索结果列表，包含内容和标记信息，按相关性排序
    """
    
    logger.info(f"开始从知识库检索: '{question[:50]}...' (数据集: {dataset_name}, top_k: {top_k})")
    try:
        dataset_id = await get_dataset_id(address, dataset_name, api_key)
        if not dataset_id:
            logger.warning(f"未找到数据集: {dataset_name}")
            return []

        retrieval_url = f"http://{address}/api/v1/retrieval"
        
        # 准备请求数据
        payload = {
            "question": question,
            "dataset_ids": [dataset_id],
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
            "key_words": key_words
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        logger.debug(f"发送检索请求: {retrieval_url}")
        # 发送异步POST请求
        async with aiohttp.ClientSession() as session:
            async with session.post(retrieval_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    retrieval_data = await response.json()
                    all_content = sorted(
                        retrieval_data['data']['chunks'],
                        key=lambda x: x['vector_similarity'],
                        reverse=True
                    )
                    # 添加相似度标记
                    results = []
                    for content in all_content:
                        similarity = content['vector_similarity']
                        results.append({
                            'content': content['content'],
                            'similarity': similarity,
                            'low_similarity': similarity < similarity_threshold
                        })
                    logger.info(f"检索完成: 找到 {len(results)} 条结果 (数据集: {dataset_name})")
                    # print(f"检索 query:{question} 检索结果: {results[:5]}\n\n")
                    # 记录低相似度结果的数量
                    low_similarity_count = sum(1 for r in results if r['low_similarity'])
                    if low_similarity_count > 0:
                        logger.warning(f"有 {low_similarity_count} 条结果的相似度低于阈值 {similarity_threshold}")
                    return results
                else:
                    logger.error(f"检索请求失败，状态码: {response.status}")
                    return []
    except Exception as e:
        logger.error(f"检索异常: {e}", exc_info=True)
        return [] 