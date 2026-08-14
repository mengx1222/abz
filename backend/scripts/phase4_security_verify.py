"""Phase 4 安全中间件验证脚本。"""
import asyncio
import sys
sys.path.insert(0, '/home/z/my-project/backend')

# 设置 Demo 模式
import os
os.environ["AZB_DEMO_MODE"] = "true"
os.environ["AZB_DATABASE_URL"] = "sqlite+aiosqlite:///data/test.db"

async def main():
    from app.core.sanitize import mask_phone, mask_id_card, mask_name, mask_email

    print("=== Phase 4 安全功能验证 ===")

    # 测试脱敏
    print("\n--- 数据脱敏测试 ---")
    assert mask_phone("13800138000") == "138****8000", f"phone: {mask_phone('13800138000')}"
    assert mask_id_card("310115199001011234") == "310***********1234", f"id: {mask_id_card('310115199001011234')}"
    assert mask_name("张三") == "张*", f"name2: {mask_name('张三')}"
    assert mask_name("张三丰") == "张*丰", f"name3: {mask_name('张三丰')}"
    assert mask_email("zhangsan@example.com") == "z***@example.com", f"email: {mask_email('zhangsan@example.com')}"
    print("  ✅ 所有脱敏函数正确")

    # 测试 Rate Limiter
    print("\n--- Rate Limiter 测试 ---")
    from app.core.rate_limit import TokenBucketRateLimiter
    bucket = TokenBucketRateLimiter(rate=2.0, capacity=5)
    # 填满
    acquired = 0
    for _ in range(10):
        if bucket.acquire():
            acquired += 1
    print(f"  容量5: 成功获取 {acquired}, 应为5")
    assert acquired == 5

    import time
    time.sleep(0.5)  # 等待补充
    acquired2 = bucket.acquire()
    print(f"  等待0.5s后: {'成功' if acquired2 else '失败'}")

    # 测试应用启动
    print("\n--- 应用启动测试 ---")
    try:
        from app.main import app
        print(f"  ✅ FastAPI app 加载成功: {app.title}")
        # 列出所有路由
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        print(f"  总路由数: {len(routes)}")
    except Exception as e:
        print(f"  ❌ App 加载失败: {e}")
        raise

    print("\n✅ 所有安全功能验证通过!")

if __name__ == "__main__":
    asyncio.run(main())
