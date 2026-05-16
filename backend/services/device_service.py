from dataclasses import dataclass
import os
import httpx
import uuid
import time
from core.config import config
from repositories.device_repo import DeviceRepo
from core.exceptions import AppException
from repositories.auth_models import (
    GetOrCreateUserInput,
)
from models.auth_model import (
    WXLoginRequset,
    WXLoginResponse
)


class DeviceService:
    def __init__(self, device_repo: DeviceRepo, logger):
        self.logger = logger
        self.device_repo: DeviceRepo = device_repo

    async def verify_device_id(self, device_id: str) -> bool:
        """检查设备ID是否存在于数据库中

        Args:
            device_id: 设备唯一标识

        Returns:
            设备是否存在
        """
        return await self.device_repo.verify_device_id(device_id)

    async def get_device_status(self, device_id: str) -> str:
        """获取设备状态

        Args:
            device_id: 设备唯一标识

        Returns:
            设备状态，如果设备不存在返回 'unknown'
        """
        status = await self.device_repo.get_device_status(device_id)
        if status is None:
            return 'unknown'
        return status

    async def update_device_status(self, device_id: str, status: str) -> bool:
        """更新设备状态

        Args:
            device_id: 设备唯一标识
            status: 新的设备状态

        Returns:
            是否更新成功
        """
        return await self.device_repo.update_device_status(device_id, status)

    async def get_device_bind_info(self, device_id: str) -> str:
        """获取设备绑定的用户ID

        Args:
            device_id: 设备唯一标识

        Returns:
            用户ID，如果设备不存在或未绑定返回空字符串
        """
        user_id = await self.device_repo.get_device_bind_info(device_id)
        if user_id is None:
            return ''
        return user_id

    async def bind_device(self, device_id: str, user_id: str) -> bool:
        """绑定设备到用户

        Args:
            device_id: 设备唯一标识
            user_id: 用户ID

        Returns:
            是否绑定成功
        """
        return await self.device_repo.bind_device(device_id, user_id)

    async def unbind_device(self, device_id: str) -> bool:
        """解除设备绑定

        Args:
            device_id: 设备唯一标识

        Returns:
            是否解除成功
        """
        return await self.device_repo.unbind_device(device_id)

    async def register_device(self, device_id: str, device_name: str = None) -> bool:
        """注册新设备

        Args:
            device_id: 设备唯一标识
            device_name: 设备名称（可选）

        Returns:
            是否注册成功
        """
        return await self.device_repo.register_device(device_id, device_name)

    async def get_user_devices(self, user_id: str) -> list[dict]:
        """获取用户绑定的所有设备

        Args:
            user_id: 用户ID

        Returns:
            设备列表
        """
        return await self.device_repo.get_user_devices(user_id)

    async def handle_device_connect(self, device_id: str) -> bool:
        """处理设备连接

        Args:
            device_id: 设备唯一标识

        Returns:
            是否连接成功
        """
        # 检查设备是否存在
        exists = await self.verify_device_id(device_id)
        if not exists:
            self.logger.warning(f"设备 {device_id} 不存在")
            return False

        # 更新设备状态为 active
        await self.update_device_status(device_id, 'active')
        self.logger.info(f"设备 {device_id} 已连接")
        return True

    async def handle_device_disconnect(self, device_id: str):
        """处理设备断开连接

        Args:
            device_id: 设备唯一标识
        """
        # 更新设备状态为 offline
        await self.update_device_status(device_id, 'offline')
        self.logger.info(f"设备 {device_id} 已断开连接")
