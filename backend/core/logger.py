"""
日志系统

统一配置根日志器，所有模块通过 logging.getLogger(__name__) 使用。
- 文件：logs/YYYY-MM-DD.log，每天一个文件，记录 INFO+
- 控制台：输出 WARNING+（报错信息）
"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path

# 默认日志目录
LOG_DIR = os.path.join(Path(__file__).resolve().parent.parent, "logs")

# 格式定义
FILE_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(pathname)s:%(lineno)d\n%(message)s"
CONSOLE_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(pathname)s:%(lineno)d\n%(message)s"

# 日期格式
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class DailyFileHandler(logging.Handler):
    """每天一个日志文件，按日期命名 (logs/YYYY-MM-DD.log)"""

    def __init__(self, log_dir: str = LOG_DIR, level=logging.INFO):
        super().__init__(level)
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def emit(self, record):
        date_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d")
        filename = os.path.join(self.log_dir, f"{date_str}.log")
        try:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")
        except Exception:
            self.handleError(record)


def setup_logging(
    log_level: int = logging.INFO,
    log_dir: str = LOG_DIR,
    console_level: int = logging.WARNING,
) -> logging.Logger:
    """配置根日志系统

    Args:
        log_level: 文件日志级别，默认 INFO
        log_dir: 日志目录
        console_level: 控制台日志级别，默认 WARNING

    Returns:
        根日志器
    """
    os.makedirs(log_dir, exist_ok=True)

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设为最低，由具体处理器控制

    # 清除已有处理器（避免重复注册）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # === 文件处理器（按日期命名，记录所有 INFO+）===
    file_handler = DailyFileHandler(log_dir, log_level)
    file_handler.setFormatter(logging.Formatter(FILE_FORMAT, DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # === 控制台处理器（输出 WARNING+）===
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # === 全局异常捕获 ===
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.error("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器

    用法: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
