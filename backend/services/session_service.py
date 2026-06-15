"""会话服务层"""

import datetime
import logging
from enum import Enum
from typing import Dict

from services.memory_service import MemoryService
from services.history_service import HistoryService
from repositories.session_repo import SessionRepo


class SessionState(Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    CHATTING = "CHATTING"
    MEMORY_EXTRACTING = "MEMORY_EXTRACTING"
    ENDED = "ENDED"


class SessionService:

    def __init__(self, session_repo, logger=None, timeout_minutes=5, memory_threshold_minutes=30):
        self.session_repo:SessionRepo = session_repo
        self.timeout = datetime.timedelta(minutes=timeout_minutes)
        self.memory_threshold = datetime.timedelta(minutes=memory_threshold_minutes)
        self.logger = logger or logging.getLogger(__name__)
        
        # 内存缓存（减少DB查询）
        self.sessions_cache: Dict[str, dict] = {}
        
        # 依赖服务
        self.memory_service:MemoryService = None
        self.history_service:HistoryService = None

    def set_dependencies(self, memory_service, history_service):
        """设置依赖服务"""
        self.memory_service = memory_service
        self.history_service = history_service

    def _now(self):
        """获取带时区的当前时间"""
        return datetime.datetime.now(datetime.timezone.utc)

    async def get_session(self, user_id: str, device_id: str = "") -> dict:
        """获取或创建会话"""
        now = self._now()
        
        # 先从缓存获取
        current_session = self.sessions_cache.get(user_id)
        if not current_session:
           current_session = await self.session_repo.get_session(user_id)
        
        if (now - current_session["last_active"]) <= self.timeout:
            current_session["state"] = SessionState.STARTING.value if current_session["turn_count"] == 0 else SessionState.CHATTING.value
            self.sessions_cache[user_id] = current_session
            return current_session

        # if current_session and current_session["state"] != SessionState.ENDED.value:
        #     if (now - current_session["last_active"]) <= self.timeout:
        #         current_session["state"] = SessionState.STARTING.value if current_session["turn_count"] == 0 else SessionState.CHATTING.value
        #         self.sessions_cache[user_id] = current_session
        #         return current_session
            
        await self.session_repo.update_session(current_session["session_id"],{
            "state": SessionState.ENDED.value
        })
        # 创建新会话（只有当数据库中没有会话，或者会话状态是 ENDED 时）
        new_session = await self.session_repo.create_session(user_id, device_id)
        self.sessions_cache[user_id] = new_session
        return new_session

    async def update(self, user_id: str):
        """更新会话活跃时间"""
        session = self.sessions_cache.get(user_id)
        if not session:
            return

        now = self._now()
        session["last_active"] = now
        session["turn_count"] += 1
        
        if session["turn_count"] == 1:
            session["state"] = SessionState.CHATTING.value

        await self.session_repo.update_session(session["session_id"], {
            "last_active": now,
            "turn_count": session["turn_count"],
            "state": session["state"]
        })

    async def end_session(self, user_id: str):
        """结束会话"""
        session = self.sessions_cache.get(user_id)
        if not session:
            return

        session["state"] = SessionState.IDLE.value
        session["memory_extracted"] = False

        await self.session_repo.update_session(session["session_id"], {
            "state": SessionState.IDLE.value,
            "memory_extracted": False
        })

    async def force_extract_memory(self, user_id: str) -> int:
        """强制提取用户记忆"""
        if not self.memory_service or not self.history_service:
            self.logger.warning("[SessionService] 依赖服务未设置")
            return 0

        # 1. 获取用户最新的未提取记忆的会话
        sessions = await self.session_repo.get_unextraced_session()
        if not sessions:
            self.logger.warning(f"[SessionService] 用户 {user_id} 不存在未提取记忆的会话")
            return 0
        total_success=0
        total_failed=0
        for device_id, sessions in sessions.items():
            success_count = 0
            if device_id != user_id or user_id == "":
                continue
            for sess in sessions:
                session_id = sess["session_id"]
                user_id = sess["user_id"]
                try:
                    # 2. 获取该 session 的所有聊天记录（按时间排序）
                    history_items = await self.history_service.get_history_by_session_id(session_id)
                    if not history_items:
                        self.logger.info(f"[SessionService] 会话 {session_id} 无对话历史，跳过")
                        # 即使没有历史，也标记为已提取（避免重复处理）
                        # await self.session_repo.mark_session_memory_extracted(session_id)
                        continue

                    # 3. 格式化为文本
                    history_text = ""
                    for item in history_items:
                        role = "用户" if item["role"] == "user" else "AI"
                        # item 可能是 dict 或对象，假设有 content 和 role
                        content = item["content"] if isinstance(item, dict) else item.content
                        history_text += f"{role}: {content}\n"

                    # 4. 调用记忆提取服务
                    extracted_count = await self.memory_service.extract_memory(
                        user_id=user_id,
                        device_id=device_id,
                        history=history_text
                    )
                    self.logger.info(f"[SessionService] 会话 {session_id} 提取了 {extracted_count} 条记忆")

                    # 5. 标记该 session 的记忆已提取
                    await self.session_repo.update_session(session_id,{"memory_extracted":True})
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"[SessionService] 提取会话 {session_id} 记忆失败: {e}", exc_info=True)
                    total_failed += 1
                    # 不更新标记，留待下次重试
            # result[device_id] = success_count
            total_success += success_count

        self.logger.info(f"[SessionService] 记忆提取完成: 成功 {total_success}, 失败 {total_failed}")
        return total_success
        # print(sessions)
        # try:
        #     session_id = sessions["session_id"]
        #     sessions["state"] = SessionState.MEMORY_EXTRACTING.value

        #     # 2. 使用session_id从history表获取聊天记录
            # history_items = await self._history_service.get_history_by_session_id(session_id)
        #     if not history_items:
        #         self.logger.info(f"[SessionService] 会话 {session_id} 无对话历史")
        #         return 0

        #     # 3. 格式化聊天记录
        #     history_text = ""
        #     for item in history_items:
        #         role = "用户" if item["role"] == "user" else "AI"
        #         history_text += f"{role}: {item['content']}\n"

        #     # 4. 提取记忆
        #     count = await self._memory_service.extract_memory(
        #         user_id=user_id,
        #         device_id=sessions.get("device_id", ""),
        #         history=history_text
        #     )

        #     # 5. 更新会话状态：提取完记忆后强制结束会话
        #     sessions["memory_extracted"] = True
        #     await self.session_repo.update_session(session_id, {
        #         "state": SessionState.ENDED.value,
        #         "memory_extracted": True
        #     })

        #     # 从缓存中移除已结束的会话
        #     if user_id in self.sessions_cache:
        #         del self.sessions_cache[user_id]

        #     self.logger.info(f"[SessionService] 强制提取会话 {session_id} 记忆成功，共 {count} 条，会话已结束")

        #     return count
        # except Exception as e:
        #     self.logger.error(f"[SessionService] 强制提取记忆失败: {e}", exc_info=True)
        #     return 0

    async def extract_memory_for_expired_sessions(self) -> int:
        """为超时会话提取记忆（供外部定时任务调用）"""
        if not self._memory_service or not self._history_service:
            self.logger.warning("[SessionService] 依赖服务未设置")
            return 0

        sessions = await self.session_repo.get_sessions_needing_memory_extraction(
            threshold_minutes=int(self.memory_threshold.total_seconds() // 60)
        )

        total_count = 0
        for session in sessions:
            try:
                user_id = session["user_id"]
                history = await self._history_service.get_recent_history(user_id)
                if not history.items:
                    continue

                history_text = ""
                for item in history.items:
                    role = "用户" if item.role == "user" else "AI"
                    history_text += f"{role}: {item.content}\n"

                count = await self._memory_service.extract_memory(
                    user_id=user_id,
                    device_id=session.get("device_id", ""),
                    history=history_text
                )

                # 提取完记忆后强制结束会话
                await self.session_repo.update_session(session["session_id"], {
                    "state": SessionState.ENDED.value,
                    "memory_extracted": True
                })

                # 从缓存中移除已结束的会话
                if user_id in self.sessions_cache:
                    del self.sessions_cache[user_id]

                total_count += count
                self.logger.info(f"[SessionService] 自动提取用户 {user_id} 记忆成功，共 {count} 条，会话已结束")

            except Exception as e:
                self.logger.error(f"[SessionService] 自动提取用户 {session['user_id']} 记忆失败: {e}", exc_info=True)

        return total_count

    async def cleanup_expired_sessions(self, timeout_minutes: int = 60) -> int:
        """清理超时会话"""
        count = await self.session_repo.cleanup_expired_sessions(timeout_minutes)
        
        now = self._now()
        to_remove = [
            uid for uid, sess in self.sessions_cache.items() 
            if (now - sess["last_active"]) > datetime.timedelta(minutes=timeout_minutes)
        ]
        for uid in to_remove:
            del self.sessions_cache[uid]

        return count
