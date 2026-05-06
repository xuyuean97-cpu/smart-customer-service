"""
批量生成测试对话 → 触发用户画像提取

用法: uv run python tools/generate_test_conversations.py [user_id]
默认 user_id = user_10001
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta
from copy import deepcopy

# 确保项目根目录在 Python path 中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

USER_ID = sys.argv[1] if len(sys.argv) > 1 else "user_10001"
TENANT_ID = "default"
APP_ID = "电商主智能客服"
AGENT_ID = "电商主智能客服"

# ============================================================================
# 多维度测试对话（覆盖画像所需的购物偏好/售后/物流/情绪/价格敏感度等维度）
# ============================================================================
TEST_CONVERSATIONS = [
    # ── 维度1: 购物偏好（数码电子，高客单价） ──
    ("你们店里有便携显示器吗？我需要一个轻便的出差用",
     "亲，有的呢！我们店里有好几款便携显示器，15.6寸到17.3寸都有，支持Type-C一线直连，重量不到1kg，非常适合出差哦～您主要连接什么设备呢？",
     0.85, 14),
    ("我的是MacBook Pro，需要支持USB-C直连的那种",
     "亲亲，那推荐您这款【15.6寸4K便携屏】，Type-C一线直连MacBook，还能反向充电，不用额外接电源！现在618活动价只要1299，比平时便宜200块呢 🔥",
     0.90, 14),
    ("这个显示器的刷新率是多少？我偶尔也打游戏",
     "亲，这款是60Hz的标准刷新率呢～如果您有游戏需求，我们有另一款【17.3寸144Hz电竞便携屏】，支持FreeSync，响应时间1ms，玩游戏非常丝滑！价格1799～",
     0.88, 13),
    ("60Hz办公够用了，帮我看下有没有优惠券",
     "亲亲，我帮您查了下，目前【15.6寸4K便携屏】可以领一张满1000减80的店铺券，还能叠加满300减30跨店满减，到手1189！超划算的～",
     0.92, 13),
    ("好的下单吧，收货地址是上海市浦东新区张江高科技园区XX路100号",
     "亲，地址已确认～15.6寸4K便携屏，券后1189元。预计2-3天送达。订单已生成，您可以在「我的订单」里查看物流哦～",
     0.95, 12),

    # ── 维度2: 售后退换货（质量敏感） ──
    ("我前天收到的显示器有一个坏点，在屏幕中间位置，白色背景下很明显",
     "亲，非常抱歉给您带来不好的体验！显示器坏点属于产品质量问题，我们支持7天无理由退换。您可以选择：1）换新：我们马上发一台新的给您；2）退货退款：全额退款。您方便拍张照片吗？",
     0.80, 11),
    ("换新的吧。但是能不能顺便帮我升级到那款144Hz的？我补差价",
     "亲亲，当然可以！补差价升级完全没问题。144Hz电竞款是1799元，您之前付了1299，补500差价就行。我帮您操作换货+升级～",
     0.93, 11),
    ("好的就这样安排",
     "亲，已操作完成！新订单【17.3寸144Hz电竞屏】已生成，券后1719元。退货快递已预约，今天下午上门取件。新显示器预计2天内发出～",
     0.96, 10),

    # ── 维度3: 物流查询 ──
    ("我的订单到哪了？都三天了还没动静",
     "亲亲别着急，我帮您查一下哈～请问您的手机号后四位是？或者提供一下订单号，我马上给您查物流轨迹。",
     0.75, 9),
    ("手机尾号8888",
     "亲，查到了！您的包裹目前显示：今天上午9:30已到达上海市浦东分拨中心，正在发往张江营业点，预计今天下午3点前派送。物流状态正常～📦",
     0.82, 9),
    ("哦好的谢谢",
     "亲亲客气啦～祝您早日收到满意的宝贝！有任何问题随时找我哦 [爱心]",
     0.78, 8),

    # ── 维度4: 闲聊 + 不满情绪 ──
    ("在吗？",
     "在的亲！小店小二24小时在线，随时为您服务～请问有什么可以帮您的吗？😊",
     0.70, 7),
    ("你们这个客服系统好慢啊",
     "亲亲非常抱歉！刚才系统确实有点小卡顿，小二已经在努力处理了。您的每一条消息小二都放在心上呢～请问您是遇到了什么问题？",
     0.60, 7),

    # ── 维度5: 跨品类兴趣（蓝牙耳机） ──
    ("上次推荐的蓝牙耳机怎么样？我健身用",
     "亲，您说的是我们家那款【XT-800运动蓝牙耳机】吧？反馈很好哦！IPX7级防水，续航12小时，耳挂式设计剧烈运动也不掉。现在活动价只要299～",
     0.86, 6),
    ("音质怎么样？跟AirPods比呢",
     "亲亲，XT-800采用13mm动圈单元，低音比同价位AirPods更浑厚，适合运动听节奏感强的音乐。不过如果追求通话降噪和生态联动，AirPods更强一些～",
     0.88, 6),
    ("买一个试试",
     "好嘞亲！XT-800运动蓝牙耳机，299元，给您用了一张新人10元券，到手289。预计明天发货，后天就能收到。戴着它去健身一定很帅！💪",
     0.91, 5),

    # ── 维度6: 平台规则 ──
    ("你们店支持七天无理由退货吗？",
     "亲，支持的！大部分商品都支持签收后7天内无理由退货。不过贴身衣物拆封后不支持，退回运费由买家承担（质量问题除外）。请问您是考虑退哪件商品呢？",
     0.84, 4),
    ("我想问一下，如果收到商品后发现不是我想象的样子，可以退吗",
     "亲，当然可以的！这属于7天无理由退货范围。只要签收7天内、商品完好、配件齐全，就可以申请退货。退款会在收到退货后1-3个工作日原路返还～",
     0.83, 4),
    ("双十一买的现在还能退吗？",
     "亲亲，双十一到现在已经超过7天了呢。不过我们店铺部分商品支持超长退货期。您方便告诉我具体是哪件商品和订单号吗？我帮您查查。另外如果商品有质量问题，也可以走售后维修通道～",
     0.87, 3),

    # ── 维度7: 价格敏感 + 比价 ──
    ("有没有更大的折扣？我看京东同款只卖1100",
     "亲亲，我们这款已经是618活动价了，还叠加了券。不过既然您是回头客，我帮您再申请一张20元的老客专属券，券后1169！而且我们送Type-C线和保护套，京东不送的哦～比综合成本我们更实惠！",
     0.81, 2),
    ("好吧那下单吧",
     "好嘞亲！1169元，帮您锁定了。老客专属券已到账，预计后天到货。感谢亲亲一直以来的支持！🙏",
     0.89, 2),

    # ── 维度8: 投诉 + 负面情绪 ──
    ("你们发的什么破快递！盒子都压扁了！",
     "亲亲非常抱歉！物流暴力运输确实让人恼火，小二理解您的心情。请问里面的商品有没有受损？如果有损坏我们马上安排换新，运费我们承担。如果只是包装盒问题，我给您申请补偿～",
     0.55, 1),
    ("东西倒是没坏，但是送人用的盒子压成这样怎么送啊",
     "亲，确实太不应该了！送礼讲究体面，盒子压坏确实不合适。我帮您安排：重新发一套完整包装盒，顺丰包邮明天到；再赔您一张50元店铺无门槛券。您看这样可以吗？",
     0.72, 1),
    ("算了这次就这样吧，下次注意",
     "亲亲，谢谢您的理解和包容！50元补偿券已发放到您的账户，新的包装盒也安排发出了。我们一定会跟物流公司反馈，加强包装保护。下次您下单我亲自帮您叮嘱仓库加厚包装！[爱心]",
     0.68, 0),
]


def _classify_topic(query: str) -> str:
    topics = {
        "显示器": "product_inquiry", "下单": "order_action",
        "物流": "logistics", "退货": "after_sales", "退款": "after_sales",
        "售后": "after_sales", "优惠": "promotion", "在吗": "chitchat",
        "慢": "complaint", "耳机": "product_inquiry", "破": "complaint",
        "坏点": "after_sales", "七天": "policy_inquiry", "双十一": "promotion",
        "盒子": "complaint", "折扣": "promotion",
    }
    for kw, topic in topics.items():
        if kw in query:
            return topic
    return "other"


async def main():
    from dotenv import load_dotenv
    load_dotenv()

    # ============================================================
    # Step 1: 初始化
    # ============================================================
    from agents.ecommerce_service.context_engineering.memory_manager import memory_manager
    await memory_manager.initialize()
    print(f"[1/4] Memory Manager 已初始化")

    # ============================================================
    # Step 2: 注入测试对话
    # ============================================================
    stored = 0
    for i, (query, response, quality, days_ago) in enumerate(TEST_CONVERSATIONS):
        created_at = datetime.now() - timedelta(days=days_ago)
        run_id = str(uuid.uuid4())

        try:
            await memory_manager.store_conversation(
                application_id=APP_ID,
                user_id=USER_ID,
                run_id=run_id,
                agent_id=AGENT_ID,
                messages=query,
                response=response,
                metadata={
                    "created_at": created_at.isoformat(),
                    "quality_score": quality,
                    "source": "微信小程序",
                    "device": "iPhone 15 Pro",
                    "ip": "192.168.1.100",
                    "network_type": "5G",
                    "topic": _classify_topic(query),
                    "tenant_id": TENANT_ID,
                },
                tenant_id=TENANT_ID,
            )
            stored += 1
            if (i + 1) % 5 == 0:
                print(f"  已注入 {i+1}/{len(TEST_CONVERSATIONS)} ...")
        except Exception as e:
            print(f"  ⚠ 第{i+1}条存储失败: {e}")

    print(f"[2/4] 已注入 {stored}/{len(TEST_CONVERSATIONS)} 条测试对话")

    # ============================================================
    # Step 3: 触发画像提取
    # ============================================================
    print(f"[3/4] 正在提取用户画像...")

    try:
        from agents.ecommerce_service.context_engineering.profile.profile_extractor import (
            get_profile_extractor
        )
        extractor = get_profile_extractor()

        history = await memory_manager.get_conversation_history(
            user_id=USER_ID,
            limit=500,
        )
        print(f"  获取到 {len(history)} 条对话历史")

        if history:
            # 会话级画像
            session_profile = await extractor.extract_session_profile(
                user_id=USER_ID,
                conversations=history,
                application_id=APP_ID,
            )
            if session_profile:
                d = session_profile.model_dump() if hasattr(session_profile, 'model_dump') else session_profile
                non_empty = {k: v for k, v in d.items() if v} if isinstance(d, dict) else {}
                print(f"  会话级画像: {len(non_empty)} 个有效字段")
                for k, v in list(non_empty.items())[:10]:
                    print(f"    {k}: {str(v)[:100]}")

            # 每日聚合画像
            try:
                daily_profile = await extractor.extract_daily_profile(
                    user_id=USER_ID,
                    application_id=APP_ID,
                )
                if daily_profile:
                    d2 = daily_profile.model_dump() if hasattr(daily_profile, 'model_dump') else daily_profile
                    non_empty2 = {k: v for k, v in d2.items() if v} if isinstance(d2, dict) else {}
                    print(f"  每日画像: {len(non_empty2)} 个有效字段")
            except Exception as e:
                print(f"  每日画像: 跳过 ({e})")

            # 深度洞察画像
            try:
                insight = await extractor.extract_insight_profile(
                    user_id=USER_ID,
                    application_id=APP_ID,
                )
                if insight:
                    d3 = insight.model_dump() if hasattr(insight, 'model_dump') else insight
                    non_empty3 = {k: v for k, v in d3.items() if v} if isinstance(d3, dict) else {}
                    print(f"  深度洞察: {len(non_empty3)} 个有效字段")
                    for k, v in list(non_empty3.items())[:8]:
                        print(f"    {k}: {str(v)[:120]}")
            except Exception as e:
                print(f"  深度洞察: 跳过 ({e})")
        else:
            print("  ⚠ 未获取到对话历史")

    except Exception as e:
        print(f"  ⚠ 画像提取异常: {e}")

    # ============================================================
    # Step 4: 验证
    # ============================================================
    import httpx
    print(f"\n[4/4] 验证 API...")
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8081", timeout=30) as c:
            r = await c.post(f"/memory/v1/profile/{USER_ID}/extract", json={
                "application_id": APP_ID
            })
            print(f"  POST /profile/{USER_ID}/extract: {r.status_code}")
            d = r.json()
            print(f"  ret_msg: {d.get('ret_msg', d.get('message', '?'))}")

            r2 = await c.get(f"/memory/v1/profile/{USER_ID}")
            print(f"  GET /profile/{USER_ID}: {r2.status_code}")
            if r2.status_code == 200:
                data = r2.json()
                inner = data.get("data", data)
                profile = inner.get("profile", {})
                if profile:
                    print(f"  用户画像 ({len(profile)} 字段):")
                    for k, v in profile.items():
                        if v:
                            print(f"    {k}: {str(v)[:120]}")
                else:
                    print(f"  (画像为空或尚未生成)")
    except Exception as e:
        print(f"  ⚠ API 验证失败 (服务未启动?): {e}")

    print(f"\n✅ 完成！用户 {USER_ID}: {stored} 条对话 → 画像已生成")


if __name__ == "__main__":
    asyncio.run(main())
