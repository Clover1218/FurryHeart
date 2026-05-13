"""会话服务层"""

import datetime
from enum import Enum
from typing import Dict

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
        self.logger = logger
        
        # 内存缓存（减少DB查询）
        self.sessions_cache: Dict[str, dict] = {}
        
        # 依赖服务
        self._memory_service = None
        self._history_service:HistoryService = None

    def set_dependencies(self, memory_service, history_service):
        """设置依赖服务"""
        self._memory_service = memory_service
        self._history_service = history_service

    def _now(self):
        """获取带时区的当前时间"""
        return datetime.datetime.now(datetime.timezone.utc)

    async def get_session(self, user_id: str, device_id: str = "") -> dict:
        """获取或创建会话"""
        now = self._now()
        
        # 先从缓存获取
        cached = self.sessions_cache.get(user_id)
        if cached:
            if (now - cached["last_active"]) <= self.timeout:
                cached["state"] = SessionState.STARTING.value if cached["turn_count"] == 0 else SessionState.CHATTING.value
                return cached

        # 从数据库获取
        db_session = await self.session_repo.get_session(user_id)
        
        if db_session and db_session["state"] != SessionState.ENDED.value:
            if (now - db_session["last_active"]) <= self.timeout:
                db_session["state"] = SessionState.STARTING.value if db_session["turn_count"] == 0 else SessionState.CHATTING.value
                self.sessions_cache[user_id] = db_session
                return db_session
            

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
        """强制提取用户记忆
        
        逻辑：
        1. 从session表选取最新的未提取记忆的会话
        2. 使用session_id去history表查询对应聊天记录
        3. 根据聊天记录提取记忆
        """
        if not self._memory_service or not self._history_service:
            if self.logger:
                self.logger.warning("[SessionService] 依赖服务未设置")
            return 0

        # 1. 获取用户最新的未提取记忆的会话
        session = await self.session_repo.get_latest_unextracted_session(user_id)
        if not session:
            if self.logger:
                self.logger.warning(f"[SessionService] 用户 {user_id} 不存在未提取记忆的会话")
            return 0

        try:
            session_id = session["session_id"]
            session["state"] = SessionState.MEMORY_EXTRACTING.value

            # 2. 使用session_id从history表获取聊天记录
            history_items = await self._history_service.get_history_by_session_id(session_id)
            if not history_items:
                if self.logger:
                    self.logger.info(f"[SessionService] 会话 {session_id} 无对话历史")
                return 0

            # 3. 格式化聊天记录
            history_text = ""
            for item in history_items:
                role = "用户" if item["role"] == "user" else "AI"
                history_text += f"{role}: {item['content']}\n"

            # 4. 提取记忆
            count = await self._memory_service.extract_memory(
                user_id=user_id,
                device_id=session.get("device_id", ""),
                history=history_text
            )

            # 5. 更新会话状态：提取完记忆后强制结束会话
            session["memory_extracted"] = True
            await self.session_repo.update_session(session_id, {
                "state": SessionState.ENDED.value,
                "memory_extracted": True
            })

            # 从缓存中移除已结束的会话
            if user_id in self.sessions_cache:
                del self.sessions_cache[user_id]

            if self.logger:
                self.logger.info(f"[SessionService] 强制提取会话 {session_id} 记忆成功，共 {count} 条，会话已结束")

            return count
        except Exception as e:
            if self.logger:
                self.logger.error(f"[SessionService] 强制提取记忆失败: {e}")
            return 0

    async def extract_memory_for_expired_sessions(self) -> int:
        """为超时会话提取记忆（供外部定时任务调用）"""
        if not self._memory_service or not self._history_service:
            if self.logger:
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
                if self.logger:
                    self.logger.info(f"[SessionService] 自动提取用户 {user_id} 记忆成功，共 {count} 条，会话已结束")

            except Exception as e:
                if self.logger:
                    self.logger.error(f"[SessionService] 自动提取用户 {session['user_id']} 记忆失败: {e}")

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
