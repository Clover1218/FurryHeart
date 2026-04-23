import os
from dataclasses import dataclass
from pathlib import Path


# 加载 .env 文件
def load_env_file():
    """从 .env 文件加载环境变量"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith("#"):
                    continue
                # 解析 KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # 如果环境变量未设置，则使用 .env 中的值
                    if key not in os.environ:
                        os.environ[key] = value


# 启动时加载 .env 文件
load_env_file()


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "123456"
    database: str = "heartbottest"
    min_size: int = 2
    max_size: int = 10
    command_timeout: int = 30
    
    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "123456"),
            database=os.getenv("DB_NAME", "heartbottest"),
            min_size=int(os.getenv("DB_MIN_SIZE", "2")),
            max_size=int(os.getenv("DB_MAX_SIZE", "10")),
            command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "30"))
        )


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6380
    password: str = "123456"
    db: int = 0
    
    @classmethod
    def from_env(cls) -> "RedisConfig":
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6380")),
            password=os.getenv("REDIS_PASSWORD", "123456"),
            db=int(os.getenv("REDIS_DB", "0"))
        )


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        return cls(
            host=os.getenv("SERVER_HOST", "127.0.0.1"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            reload=os.getenv("SERVER_RELOAD", "false").lower() == "true"
        )


@dataclass
class LogConfig:
    level: str = "INFO"
    file: str = "logs/app.log"
    
    @classmethod
    def from_env(cls) -> "LogConfig":
        return cls(
            level=os.getenv("LOG_LEVEL", "INFO"),
            file=os.getenv("LOG_FILE", "logs/app.log")
        )


@dataclass
class AppConfig:
    db: DatabaseConfig
    redis: RedisConfig
    server: ServerConfig
    log: LogConfig
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            db=DatabaseConfig.from_env(),
            redis=RedisConfig.from_env(),
            server=ServerConfig.from_env(),
            log=LogConfig.from_env()
        )


# 全局配置实例
config = AppConfig.from_env()
