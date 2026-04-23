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

from repositories.auth_models import (
    GetOrCreateUserInput,
    GetOrCreateUserOutput,
    GetUserInput,
    GetUserOutput,
    SaveTokenInput,
    SaveTokenOutput,
    GetTokenInput,
    GetTokenOutput,
    DeleteTokenInput,
    DeleteTokenOutput
)
from core.exceptions import AppException


class AuthRepo:

    def __init__(self, db_pool,redis_client):
        self.db = db_pool
        self.redis=redis_client

    async def get_or_create_user(self, input_data: GetOrCreateUserInput) -> GetOrCreateUserOutput:
        """根据 openid 查询或创建用户"""
        if not input_data.open_id:
            raise AppException(message="open_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                # 先查询用户是否存在
                existing_user = await conn.fetchrow(
                    "SELECT user_id FROM user_info WHERE open_id = $1",
                    input_data.open_id
                )
                
                if existing_user:
                    user_id = existing_user['user_id']
                    return GetOrCreateUserOutput(user_id=str(user_id),)
                else:
                    # 生成随机昵称
                    nickname = self._generate_nickname()
                    user_id= new_snowflake_id()
                    logging.info(user_id)
                    # 插入新用户
                    await conn.execute(
                        """
                        INSERT INTO user_info (user_id, open_id, nickname, avatar_url)
                        VALUES ($1, $2, $3 ,$4)
                        """,
                        user_id,input_data.open_id, nickname, ""
                    )
                    return GetOrCreateUserOutput(user_id=str(user_id),)
                
            except asyncpg.UniqueViolationError as e:
                raise AppException(message="用户已存在", code=409) from e
            except asyncpg.PostgresError as e:
                logging.error(f"数据库操作失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e

    async def get_user(self, input_data: GetUserInput) -> GetUserOutput:
        """根据 openid 获取用户"""
        if not input_data.open_id:
            raise AppException(message="open_id 不能为空", code=400)
        
        async with self.db.acquire() as conn:
            try:
                # 查询用户是否存在
                existing_user = await conn.fetchrow(
                    "SELECT user_id FROM user_info WHERE open_id = $1",
                    input_data.open_id
                )
                
                if existing_user:
                    user_id = existing_user['user_id']
                    return GetUserOutput(user_id=str(user_id), exist=True)
                else:
                    return GetUserOutput(user_id="", exist=False)
                
            except asyncpg.PostgresError as e:
                logging.error(f"数据库操作失败: {e}")
                raise AppException(message="数据库操作失败", code=500) from e

    def _generate_token(self) -> str:
        """生成唯一 token"""
        return uuid.uuid4().hex

    def _generate_nickname(self) -> str:
        """生成随机昵称"""
        prefix = "用户"
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        return f"{prefix}{suffix}"
    
    async def save_token(self, input_data: SaveTokenInput) -> SaveTokenOutput:
        """保存 token 到 Redis"""
        if not self.redis:
            return SaveTokenOutput(success=False)
        token=self._generate_token()
        key = f"auth:token:{token}"
        value = json.dumps({
            "user_id": input_data.user_id,
            "created_at": datetime.now().isoformat()
        })
        
        # 设置过期时间（秒）
        expire_seconds = input_data.expire_days * 24 * 60 * 60
        
        try:
            await self.redis.set(key, value, ex=expire_seconds)
            return SaveTokenOutput(token=token,success=True)
        except Exception as e:
            logging.error(f"保存 token 失败: {e}")
            raise AppException(message="数据库操作失败", code=500) from e
    
    async def get_token(self, input_data: GetTokenInput) -> GetTokenOutput:
        """从 Redis 获取 token 信息"""
        if not self.redis:
            return GetTokenOutput(exist=False)
        
        key = f"auth:token:{input_data.token}"
        
        try:
            value = await self.redis.get(key)
            if value:
                data = json.loads(value)
                return GetTokenOutput(
                    user_id=data.get("user_id"),
                    exist=True
                )
            return GetTokenOutput(exist=False)
        except Exception as e:
            logging.error(f"获取 token 失败: {e}")
            return GetTokenOutput(exist=False)
    
    async def delete_token(self, input_data: DeleteTokenInput) -> DeleteTokenOutput:
        """从 Redis 删除 token"""
        if not self.redis:
            return DeleteTokenOutput(success=False)
        
        key = f"auth:token:{input_data.token}"
        
        try:
            await self.redis.delete(key)
            return DeleteTokenOutput(success=True)
        except Exception as e:
            logging.error(f"删除 token 失败: {e}")
            return DeleteTokenOutput(success=False)
