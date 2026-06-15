import asyncpg
import logging
logger = logging.getLogger(__name__)
from core.config import config
import redis.asyncio as redis

async def create_pool():
    """创建数据库连接池（使用原始参数，非 DSN）"""
    pool = await asyncpg.create_pool(
        host=config.db.host,
        port=config.db.port,
        user=config.db.user,
        password=config.db.password,
        database=config.db.database,
        min_size=config.db.min_size,
        max_size=config.db.max_size,
        command_timeout=config.db.command_timeout
    )
    logger.info(f"数据库连接池初始化完成: {config.db.host}:{config.db.port}/{config.db.database}")
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
        logger.info("Redis连接初始化完成")
        return redis_client
    except Exception as e:
        redis_client = None
        return redis_client
