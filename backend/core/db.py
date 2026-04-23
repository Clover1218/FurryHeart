import asyncpg
import logging
from core.config import config
import redis.asyncio as redis

async def create_pool(db_url: str = None):
    """创建数据库连接池
    
    Args:
        db_url: 数据库连接字符串，如果为None则使用配置文件中的DSN
    """
    if db_url is None:
        db_url = config.db.dsn
    
    pool = await asyncpg.create_pool(
        dsn=db_url,
        min_size=config.db.min_size,
        max_size=config.db.max_size,
        command_timeout=config.db.command_timeout
    )
    logging.info(f"数据库连接池初始化完成: {config.db.host}:{config.db.port}/{config.db.database}")
    return pool

async def create_redis_client():
    redis_client = None
    try:
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            decode_responses=True
        )
        await redis_client.ping()
        logging.info("Reids连接初始化完成")
        return redis_client
    except Exception as e:
        redis_client = None
        return redis_client

