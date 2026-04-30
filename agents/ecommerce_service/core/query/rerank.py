import aiohttp
from common.logging import get_logger

# 获取重排序专用日志记录器
logger = get_logger("agents.utils.rerank")


# async def rerank_results(results, user_question,reranker_model=None,reranker_address=None,api_key=None,top_k=5):
#     """
#     异步重排序函数，使用 HTTP API 调用重排序模型
#     """
#     logger.info(f"开始重排序 - 文档数量: {len(results)}, 查询: {user_question},重排序模型: {reranker_model},重排序地址: {reranker_address},api_key: {api_key}")

#     if not reranker_address or not reranker_model or not api_key:
#         logger.warning("重排序模型配置缺失，跳过重排序")
#         return results

#     # 构建文档列表
#     documents = [item['content'].strip()[:500] for item in results]
#     logger.info(f"准备重排序 - 模型: {reranker_model}, 地址: {reranker_address}")
#     # 构建 API 请求体
#     payload = {
#         "model": reranker_model,
#         "query": user_question,
#         "documents": documents,
#         "top_n": top_k
#     }
#     try:
#         async with aiohttp.ClientSession() as session:
#             headers = {
#                 'Content-Type': 'application/json'
#             }
#             if api_key:
#                 headers['Authorization'] = f'Bearer {api_key}'

#             async with session.post(reranker_address, json=payload, headers=headers) as response:
#                 if response.status == 200:
#                     result_data = await response.json()
#                     logger.info("重排序API调用成功")

#                     # 根据重排序结果重新排列原始结果
#                     if 'results' in result_data:
#                         reranked_results = [{"content": documents[item["index"]], "similarity": item['relevance_score']} for item in result_data['results']]
#                         # 确保有结果再取最大值
#                         if reranked_results:
#                             max_similarity = max(item["similarity"] for item in reranked_results)
#                             logger.info(f"重排序完成 - 结果数量: {len(reranked_results)}, 最高相似度: {max_similarity:.4f}")
#                             return reranked_results, max_similarity
#                         else:
#                             logger.warning("重排序结果为空")
#                         return results[:top_k],max_similarity
#                     else:
#                         logger.error("重排序响应格式异常，使用原始结果")
#                         return results[:top_k], 0.0
#                 else:
#                     logger.error(f"重排序 API 调用失败，状态码: {response.status}")
#                     error_text = await response.text()
#                     logger.error(f"错误详情: {error_text}")
#                     return results[:top_k], 0.0

#     except Exception as e:
#         logger.error(f"重排序过程发生错误: {str(e)}")
#         return results[:top_k], 0.0
async def rerank_results(results, user_question, reranker_model=None, reranker_address=None, api_key=None, top_k=5):
    """
    异步重排序函数，使用 HTTP API 调用重排序模型 (适配阿里云 DashScope)
    """
    logger.info(f"开始重排序 - 文档数量: {len(results)}, 查询: {user_question}, 模型: {reranker_model}")

    if not reranker_address or not reranker_model or not api_key:
        logger.warning("重排序模型配置缺失，跳过重排序")
        return results, 0.0

    # 构建文档列表 (保持原有逻辑，截取前500字符)
    documents = [item['content'].strip()[:500] for item in results]

    # --- 核心修改 1: 构造符合 DashScope 要求的 payload ---
    payload = {
        "model": reranker_model,
        "input": {
            "query": user_question,
            "documents": documents
        },
        "parameters": {


            "return_documents": False, # 不需要API返回文档文本，我们要自己根据index映射
            "top_n": top_k
        }
    }
    # --------------------------------------------------

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }

            async with session.post(reranker_address, json=payload, headers=headers) as response:
                if response.status == 200:
                    result_data = await response.json()
                    logger.info("重排序API调用成功")

                    # --- 核心修改 2: 适配 DashScope 的返回结构 (output -> results) ---
                    # 阿里云返回结构通常是: {"output": {"results": [...]}, ...}
                    rerank_data = []
                    if 'output' in result_data and 'results' in result_data['output']:
                        rerank_data = result_data['output']['results']
                    elif 'results' in result_data:
                        # 兼容部分非标准返回
                        rerank_data = result_data['results']

                    if rerank_data:
                        # 根据 index 重新组装结果
                        reranked_results = []
                        for item in rerank_data:
                            idx = item.get("index")
                            score = item.get("relevance_score")
                            if idx is not None and idx < len(documents):
                                reranked_results.append({
                                    "content": documents[idx],
                                    "similarity": score,
                                    # 如果原始 results 里有 metadata，最好也带上
                                    # "metadata": results[idx].get('metadata', {})
                                })

                        if reranked_results:
                            max_similarity = reranked_results[0]['similarity'] # 结果通常已按分数排序
                            logger.info(f"重排序完成 - 结果数量: {len(reranked_results)}, 最高相似度: {max_similarity:.4f}")
                            return reranked_results, max_similarity
                    # -----------------------------------------------------------

                    logger.warning("重排序结果为空或解析失败，使用原始结果")
                    return results[:top_k], 0.0
                else:
                    logger.error(f"重排序 API 调用失败，状态码: {response.status}")
                    error_text = await response.text()
                    logger.error(f"错误详情: {error_text}")
                    return results[:top_k], 0.0

    except Exception as e:
        logger.error(f"重排序过程发生错误: {str(e)}")
        # 发生异常时返回原始结果，避免系统中断
        return results[:top_k], 0.0
