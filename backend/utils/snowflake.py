import os
from snowflake import SnowflakeGenerator

# 从环境变量获取 worker_id，默认使用 1（0-1023 范围）
WORKER_ID = int(os.getenv("SNOWFLAKE_WORKER_ID", "1"))

# 创建全局生成器（每个进程/实例一个）
_generator = SnowflakeGenerator(WORKER_ID)


def new_snowflake_id() -> int:
    """生成一个新的雪花 ID（64 位整数）"""
    return next(_generator)


def parse_snowflake_id(id: int) -> dict:
    """解析雪花 ID，返回时间戳、worker_id、序列号等信息"""
    from snowflake import Snowflake
    sf = Snowflake.parse(id)
    return {
        "timestamp": sf.datetime,
        "worker_id": sf.instance,
        "sequence": sf.seq,
    }