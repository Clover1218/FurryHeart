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


@dataclass(frozen=True)
class CreateBindTokenInput:
    user_id: str


@dataclass(frozen=True)
class CreateBindTokenOutput:
    token: str


@dataclass(frozen=True)
class ValidateDeviceBindInput:
    token: str


@dataclass(frozen=True)
class ValidateDeviceBindOutput:
    user_id: Optional[str] = None
    exists: bool = False


@dataclass(frozen=True)
class ValidateDeviceIdInput:
    device_id: str


@dataclass(frozen=True)
class ValidateDeviceIdOutput:
    exists: bool


@dataclass(frozen=True)
class CheckDeviceBindInfoInput:
    device_id: str
    user_id: str


@dataclass(frozen=True)
class CheckDeviceBindInfoOutput:
    id: str
    bind_state: bool


@dataclass(frozen=True)
class BindDeviceInput:
    device_id: str
    user_id: str
    extra_meta: Optional[dict] = None


@dataclass(frozen=True)
class BindDeviceOutput:
    id: str
    success: bool


@dataclass(frozen=True)
class UnbindDeviceInput:
    device_id: str
    user_id: str


@dataclass(frozen=True)
class UnbindDeviceOutput:
    success: bool


@dataclass(frozen=True)
class CheckDeviceStatusInput:
    device_id: str


@dataclass(frozen=True)
class CheckDeviceStatusOutput:
    status: int
    last_online_at: Optional[datetime] = None


@dataclass(frozen=True)
class SetDeviceStatusInput:
    device_id: str
    status: int  # 0: 离线 1: 在线 2: 禁用


@dataclass(frozen=True)
class SetDeviceStatusOutput:
    success: bool


class DeviceRepo:

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db = db_pool
        self.redis = redis_client
    async def validate_device_bind(self, input_data: ValidateDeviceBindInput) -> ValidateDeviceBindOutput:
        """验证设备绑定 token
        
        Args:
            input_data: 包含 token 的输入
            
        Returns:
            ValidateDeviceBindOutput: 包含 user_id 和是否存在的信息
        """
        if not input_data.token:
            raise AppException(message="token 不能为空", code=400)
        
        if not self.redis:
            return ValidateDeviceBindOutput(exists=False)
        
        try:
            # 构建 Redis 键
            key = f"device:token:{input_data.token}"
            
            # 获取值
            user_id = await self.redis.get(key)
            
            if user_id:
                return ValidateDeviceBindOutput(
                    user_id=user_id,
                    exists=True
                )
            return ValidateDeviceBindOutput(exists=False)
            
        except Exception as e:
            logging.error(f"验证绑定 token 失败: {e}")
            return ValidateDeviceBindOutput(exists=False)
   
    async def validate_device_id(self, input_data: ValidateDeviceIdInput) -> ValidateDeviceIdOutput:
        """验证设备 id 是否存在于 device_info 表
        
        Args:
            input_data: 包含 device_id 的输入
            
        Returns:
            ValidateDeviceIdOutput: 包含是否存在的信息
        """
        if not input_data.device_id:
            raise AppException(message="device_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM device_info WHERE device_id = $1)",
                    input_data.device_id
                )
                return ValidateDeviceIdOutput(exists=result)
            except asyncpg.PostgresError as e:
                logging.error(f"验证设备 id 失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
    
    async def check_device_bind_info(self, input_data: CheckDeviceBindInfoInput) -> CheckDeviceBindInfoOutput:
        """检查设备 id 是否与某用户 user_id 绑定
        
        Args:
            input_data: 包含 device_id 和 user_id 的输入
            
        Returns:
            CheckDeviceBindInfoOutput: 包含 id 和绑定状态
        """
        if not input_data.device_id or not input_data.user_id:
            raise AppException(message="device_id 和 user_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    """
                    SELECT id, bind_state 
                    FROM user_devices 
                    WHERE device_id = $1 AND user_id = $2 AND bind_state = 1
                    """,
                    input_data.device_id, int(input_data.user_id)
                )
                
                if result:
                    return CheckDeviceBindInfoOutput(
                        id=str(result['id']),
                        bind_state=result['bind_state'] == 1
                    )
                return CheckDeviceBindInfoOutput(id="", bind_state=False)
            except asyncpg.PostgresError as e:
                logging.error(f"检查设备绑定信息失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
    
    async def bind_device(self, input_data: BindDeviceInput) -> BindDeviceOutput:
        """绑定设备到用户
        
        Args:
            input_data: 包含 device_id、user_id 和 extra_meta 的输入
            
        Returns:
            BindDeviceOutput: 包含 id 和成功状态
        """
        if not input_data.device_id or not input_data.user_id:
            raise AppException(message="device_id 和 user_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                # 检查设备是否存在
                device_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM device_info WHERE device_id = $1)",
                    input_data.device_id
                )
                
                if not device_exists:
                    raise AppException(message="设备不存在", code=404)
                
                # 检查是否已经绑定
                existing_bind = await conn.fetchrow(
                    """
                    SELECT id FROM user_devices 
                    WHERE device_id = $1 AND bind_state = 1
                    """,
                    input_data.device_id
                )
                
                if existing_bind:
                    raise AppException(message="设备已绑定", code=409)
                
                # 插入绑定记录
                result = await conn.fetchrow(
                    """
                    INSERT INTO user_devices (user_id, device_id, extra_meta)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    """,
                    int(input_data.user_id), input_data.device_id, input_data.extra_meta
                )
                print(result)
                return BindDeviceOutput(
                    id=str(result['id']),
                    success=True
                )
            except AppException:
                raise
            except asyncpg.PostgresError as e:
                logging.error(f"绑定设备失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
    
    async def unbind_device(self, input_data: UnbindDeviceInput) -> UnbindDeviceOutput:
        """解绑设备
        
        Args:
            input_data: 包含 device_id 和 user_id 的输入
            
        Returns:
            UnbindDeviceOutput: 包含成功状态
        """
        if not input_data.device_id or not input_data.user_id:
            raise AppException(message="device_id 和 user_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                # 更新绑定状态
                result = await conn.execute(
                    """
                    UPDATE user_devices 
                    SET bind_state = 0, unbind_time = NOW()
                    WHERE device_id = $1 AND user_id = $2 AND bind_state = 1
                    """,
                    input_data.device_id, input_data.user_id
                )
                
                # 检查是否更新成功
                success = result.split()[1] != '0'
                return UnbindDeviceOutput(success=success)
            except asyncpg.PostgresError as e:
                logging.error(f"解绑设备失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
    
    async def check_device_status(self, input_data: CheckDeviceStatusInput) -> CheckDeviceStatusOutput:
        """检查设备状态
        
        Args:
            input_data: 包含 device_id 的输入
            
        Returns:
            CheckDeviceStatusOutput: 包含设备状态和最后在线时间
        """
        if not input_data.device_id:
            raise AppException(message="device_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                result = await conn.fetchrow(
                    "SELECT status, last_online_at FROM device_info WHERE device_id = $1",
                    input_data.device_id
                )
                
                if result:
                    return CheckDeviceStatusOutput(
                        status=result['status'],
                        last_online_at=result['last_online_at']
                    )
                raise AppException(message="设备不存在", code=404)
            except AppException:
                raise
            except asyncpg.PostgresError as e:
                logging.error(f"检查设备状态失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
    
    async def set_device_status(self, input_data: SetDeviceStatusInput) -> SetDeviceStatusOutput:
        """设置设备状态
        
        Args:
            input_data: 包含 device_id 和 status 的输入
            
        Returns:
            SetDeviceStatusOutput: 包含成功状态
        """
        if not input_data.device_id:
            raise AppException(message="device_id 不能为空", code=400)
        
        if input_data.status not in [0, 1, 2]:
            raise AppException(message="status 必须是 0、1 或 2", code=400)
        
        async with self.db.acquire() as conn:
            try:
                # 构建更新语句
                update_fields = ["status = $1"]
                update_values = [input_data.status]
                
                # 如果设置为在线，更新最后在线时间
                if input_data.status == 1:
                    update_fields.append("last_online_at = NOW()")
                
                # 执行更新
                result = await conn.execute(
                    f"""
                    UPDATE device_info 
                    SET {', '.join(update_fields)}
                    WHERE device_id = ${len(update_values) + 1}
                    """,
                    *update_values, input_data.device_id
                )
                
                # 检查是否更新成功
                success = result.split()[1] != '0'
                return SetDeviceStatusOutput(success=success)
            except AppException:
                raise
            except asyncpg.PostgresError as e:
                logging.error(f"设置设备状态失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e
