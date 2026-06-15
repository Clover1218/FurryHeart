"""定时任务调度器"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def add_hourly_task(name: str, func: Callable):
    """添加每小时执行的任务"""
    scheduler.add_job(
        func,
        CronTrigger(minute=0),  # 每小时整点执行
        id=name,
        name=name,
        replace_existing=True
    )
    logger.info(f"定时任务 [{name}] 已添加，每小时执行一次")


def add_daily_task(name: str, func: Callable, hour: int = 0, minute: int = 0):
    """添加每天执行的任务"""
    scheduler.add_job(
        func,
        CronTrigger(hour=hour, minute=minute),
        id=name,
        name=name,
        replace_existing=True
    )
    logger.info(f"定时任务 [{name}] 已添加，每天 {hour:02d}:{minute:02d} 执行")


def add_interval_task(name: str, func: Callable, minutes: int):
    """添加间隔执行的任务"""
    scheduler.add_job(
        func,
        "interval",
        minutes=minutes,
        id=name,
        name=name,
        replace_existing=True
    )
    logger.info(f"定时任务 [{name}] 已添加，每 {minutes} 分钟执行一次")


def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        scheduler.start()
        logger.info("定时任务调度器已启动")


def shutdown_scheduler():
    """关闭调度器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已关闭")


def get_scheduler_jobs():
    """获取所有任务列表"""
    return scheduler.get_jobs()
