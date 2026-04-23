import asyncio
from core.db import create_pool
from core.config import config

async def add_test_device():
    """添加测试设备到数据库"""
    print("正在连接数据库...")
    
    try:
        # 创建数据库连接池
        pool = await create_pool()
        print(f"数据库连接成功: {config.db.host}:{config.db.port}/{config.db.database}")
        
        async with pool.acquire() as conn:
            # 检查设备是否已存在
            existing = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM device_info WHERE device_id = $1)",
                "test"
            )
            
            if existing:
                print("测试设备 'test' 已存在")
            else:
                # 插入测试设备
                await conn.execute(
                    """
                    INSERT INTO device_info (device_id, device_name, status)
                    VALUES ($1, $2, $3)
                    """,
                    "test", "测试设备", 1  # 1: 在线状态
                )
                print("测试设备 'test' 添加成功")
        
        # 关闭连接池
        await pool.close()
        print("数据库连接池已关闭")
        
    except Exception as e:
        print(f"操作失败: {e}")

if __name__ == "__main__":
    asyncio.run(add_test_device())
