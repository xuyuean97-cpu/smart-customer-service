# import asyncio
# import asyncpg

# # === 这里直接使用了你提供的配置 ===
# DB_CONFIG = {
#     "user": "postgres",
#     "password": "245969",      # 你提供的密码
#     "database": "test",        # 你提供的数据库名
#     "host": "localhost",
#     "port": 5432,
# }

# async def check_data():
#     print("=" * 50)
#     print(f"🕵️‍♂️ 正在尝试连接数据库: {DB_CONFIG['database']} @ {DB_CONFIG['host']}...")

#     conn = None
#     try:
#         # 1. 尝试连接
#         conn = await asyncpg.connect(**DB_CONFIG)
#         print("✅ 连接成功！")

#         # 2. 检查当前库里到底有什么表
#         print("\n[检查 1] 查看当前库中的表:")
#         tables = await conn.fetch("""
#             SELECT table_name
#             FROM information_schema.tables
#             WHERE table_schema = 'public'
#         """)

#         if not tables:
#             print("❌ 警告：当前库 'test' 里是空的！没有任何表！")
#             print("   -> 请检查你的 Navicat/DBeaver 是否把数据建在 'postgres' 库里了？")
#             return

#         table_names = [t['table_name'] for t in tables]
#         print(f"   发现表: {table_names}")

#         # 3. 检查 orders 表是否存在
#         if 'orders' in table_names:
#             # 4. 检查 orders 表里的具体数据
#             print("\n[检查 2] 查询 orders 表前 5 条数据:")
#             rows = await conn.fetch("SELECT * FROM orders LIMIT 5")
#             if not rows:
#                 print("   ⚠️ 表存在，但里面是空的 (0 rows)！")
#             else:
#                 for row in rows:
#                     print(f"   - {dict(row)}")

#             # 5. 精确查找那个报错的订单号
#             target_id = '202310240001'
#             print(f"\n[检查 3] 寻找指定订单: {target_id}")
#             # 注意：这里强转字符串查询，排除类型问题
#             specific = await conn.fetch(f"SELECT * FROM orders WHERE order_id::text = '{target_id}'")
#             if specific:
#                 print(f"   ✅ 找到了！数据如下:\n   {dict(specific[0])}")
#             else:
#                 print(f"   ❌ 依然没找到订单 {target_id}。")
#                 print("   -> 请确认你插入数据时是否带了空格？或者 ID 是不是这个？")
#         else:
#             print(f"\n❌ 致命错误：当前库 '{DB_CONFIG['database']}' 中没有 'orders' 表！")

#     except asyncpg.InvalidCatalogNameError:
#         print(f"\n❌ 连接失败：数据库 '{DB_CONFIG['database']}' 不存在！")
#         print("   -> 请在数据库软件中确认数据库名称是否真的是 'test'。")
#     except asyncpg.InvalidPasswordError:
#         print("\n❌ 连接失败：密码错误！")
#     except Exception as e:
#         print(f"\n❌ 发生其他错误: {e}")
#     finally:
#         if conn:
#             await conn.close()
#         print("=" * 50)

# if __name__ == "__main__":
#     asyncio.run(check_data())

import chromadb
import json

# --- 根据你的报错信息更新了IP ---
# 这里的 IP 是你报错日志中显示的 8.162.3.14
CONV_DB_HOST = "8.162.3.14"
CONV_DB_PORT = 8000
CONV_COLLECTION = "conversation_memory"

PROFILE_DB_HOST = "8.162.3.14" # 假设画像也在同一台机器
PROFILE_DB_PORT = 8000
PROFILE_COLLECTION = "profile_memory"

def dump_collection(host, port, collection_name, output_file):
    print(f"正在连接 {host}:{port} 获取集合 [{collection_name}]...")
    try:
        # 连接数据库
        client = chromadb.HttpClient(host=host, port=port)

        # 检查集合是否存在
        try:
            # 尝试直接获取，如果不存在会报错或返回空
            collection = client.get_collection(name=collection_name)
        except Exception:
            print(f"⚠️ 警告: 无法找到集合 {collection_name}，跳过。")
            return

        # --- 核心修改在这里 ---
        # 1. include 参数去掉 "ids"
        # 2. limit=None 表示获取所有数据
        all_data = collection.get(limit=None, include=["documents", "metadatas"])

        ids = all_data.get('ids', [])
        count = len(ids)
        print(f"✅ 成功获取 {count} 条记录。")

        if count == 0:
            print("数据为空，跳过保存。")
            return

        # 转换为易读的列表格式
        export_list = []
        for i in range(count):
            item = {
                "id": ids[i],
                # 兼容处理：防止某些数据没有 document 或 metadata
                "content": all_data.get('documents', [])[i] if all_data.get('documents') else "",
                "metadata": all_data.get('metadatas', [])[i] if all_data.get('metadatas') else {}
            }
            export_list.append(item)

        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_list, f, ensure_ascii=False, indent=2)
        print(f"💾 数据已保存至: {output_file}\n")

    except Exception as e:
        print(f"❌ 获取失败: {e}\n")

if __name__ == "__main__":
    # 导出对话记忆
    dump_collection(CONV_DB_HOST, CONV_DB_PORT, CONV_COLLECTION, "all_conversations.json")

    # 导出画像记忆
    dump_collection(PROFILE_DB_HOST, PROFILE_DB_PORT, PROFILE_COLLECTION, "all_profiles.json")
