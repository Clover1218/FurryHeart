import asyncio
from core.db import create_pool
from core.config import config


async def test_db_connection():
    """测试数据库连接和表结构"""
    print("正在测试数据库连接...")
    
    try:
        # 创建数据库连接池
        pool = await create_pool()
        print(f"数据库连接成功: {config.db.host}:{config.db.port}/{config.db.database}")
        
        # 检查 user_info 表是否存在
        async with pool.acquire() as conn:
            # 检查表是否存在
            result = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'user_info'
                )
                """
            )
            
            if result:
                print("user_info 表存在")
                
                # 查看表结构
                columns = await conn.fetch(
                    """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_info'
                    ORDER BY ordinal_position
                    """
                )
                print("表结构:")
                for col in columns:
                    print(f"  {col['column_name']}: {col['data_type']}")
            else:
                print("错误: user_info 表不存在！")
                print("请先创建表结构:")
                print("""
                CREATE TABLE "user_info" (
                    user_id BIGINT PRIMARY KEY,                     -- 雪花ID作为主键
                    openid VARCHAR(64) NOT NULL UNIQUE,        -- 微信openid
                    nickname VARCHAR(64),
                    avatar_url VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)
        
        # 关闭连接池
        await pool.close()
        print("数据库连接池已关闭")
        
    except Exception as e:
        print(f"数据库连接失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_db_connection())
