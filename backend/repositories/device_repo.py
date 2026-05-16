import asyncpg
import json
import uuid
import random
import string
from typing import Optional
import redis.asyncio as redis
from dataclasses import dataclass
from datetime import datetime, timedelta
from utils.snowflake import new_snowflake_id, parse_snowflake_id
import logging

from core.exceptions import AppException


@dataclass
class ValidateDeviceIdInput:
    device_id: str


@dataclass
class ValidateDeviceIdOutput:
    success: bool
    message: str


@dataclass
class CheckDeviceStatusInput:
    device_id: str


@dataclass
class CheckDeviceStatusOutput:
    success: bool
    status: Optional[str]
    message: str


@dataclass
class SetDeviceStatusInput:
    device_id: str
    status: str


@dataclass
class SetDeviceStatusOutput:
    success: bool
    message: str


@dataclass
class CheckDeviceBindInfoInput:
    device_id: str


@dataclass
class CheckDeviceBindInfoOutput:
    success: bool
    user_id: Optional[str]
    message: str


@dataclass
class BindDeviceInput:
    device_id: str
    user_id: str


@dataclass
class BindDeviceOutput:
    success: bool
    message: str


class DeviceRepo:

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db = db_pool
        self.redis = redis_client

    async def verify_device_id(self, device_id: str) -> bool:
        """检查设备ID是否存在于数据库中

        Args:
            device_id: 设备唯一标识

        Returns:
            设备是否存在
        """
        query = """
        SELECT 1 FROM device_info WHERE device_id = $1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, device_id)
            return row is not None

    async def get_device_status(self, device_id: str) -> Optional[str]:
        """获取设备状态

        Args:
            device_id: 设备唯一标识

        Returns:
            设备状态，如果设备不存在返回 None
        """
        query = """
        SELECT status FROM device_info WHERE device_id = $1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, device_id)
            if row:
                return row['status']
            return None

    async def update_device_status(self, device_id: str, status: str) -> bool:
        """更新设备状态

        Args:
            device_id: 设备唯一标识
            status: 新的设备状态

        Returns:
            是否更新成功
        """
        query = """
        UPDATE device_info 
        SET status = $1, 
            last_connected_at = NOW(),
            updated_at = NOW()
        WHERE device_id = $2
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, status, device_id)
            return result != "UPDATE 0"

    async def get_device_bind_info(self, device_id: str) -> Optional[str]:
        """获取设备绑定的用户ID

        Args:
            device_id: 设备唯一标识

        Returns:
            用户ID，如果设备不存在或未绑定返回 None
        """
        query = """
        SELECT user_id FROM device_info WHERE device_id = $1
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, device_id)
            if row:
                return row['user_id']
            return None

    async def bind_device(self, device_id: str, user_id: str) -> bool:
        """绑定设备到用户

        Args:
            device_id: 设备唯一标识
            user_id: 用户ID

        Returns:
            是否绑定成功
        """
        query = """
        UPDATE device_info 
        SET user_id = $1, 
            status = 'active',
            updated_at = NOW()
        WHERE device_id = $2
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, user_id, device_id)
            return result != "UPDATE 0"

    async def unbind_device(self, device_id: str) -> bool:
        """解除设备绑定

        Args:
            device_id: 设备唯一标识

        Returns:
            是否解除成功
        """
        query = """
        UPDATE device_info 
        SET user_id = NULL, 
            status = 'offline',
            updated_at = NOW()
        WHERE device_id = $1
        """
        async with self.db.acquire() as conn:
            result = await conn.execute(query, device_id)
            return result != "UPDATE 0"

    async def register_device(self, device_id: str, device_name: str = None) -> bool:
        """注册新设备

        Args:
            device_id: 设备唯一标识
            device_name: 设备名称（可选）

        Returns:
            是否注册成功（如果设备已存在也返回 True）
        """
        # 先检查设备是否已存在
        if await self.verify_device_id(device_id):
            return True

        query = """
        INSERT INTO device_info (device_id, device_name, status)
        VALUES ($1, $2, 'offline')
        """
        try:
            async with self.db.acquire() as conn:
                await conn.execute(query, device_id, device_name or device_id)
                return True
        except asyncpg.UniqueViolationError:
            # 并发注册时可能冲突，忽略
            return True

    async def get_user_devices(self, user_id: str) -> list[dict]:
        """获取用户绑定的所有设备

        Args:
            user_id: 用户ID

        Returns:
            设备列表
        """
        query = """
        SELECT device_id, device_name, status, last_connected_at, created_at
        FROM device_info 
        WHERE user_id = $1
        ORDER BY created_at DESC
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, user_id)
            devices = []
            for row in rows:
                devices.append({
                    'device_id': row['device_id'],
                    'device_name': row['device_name'],
                    'status': row['status'],
                    'last_connected_at': row['last_connected_at'].isoformat() if row['last_connected_at'] else None,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None
                })
            return devices
