import datetime
import uuid


class SessionState:
    IDLE = "IDLE"
    STARTING = "STARTING"
    CHATTING = "CHATTING"


class SessionService:

    def __init__(self, timeout_minutes=5):
        self.sessions = {}  # user_id -> session
        self.timeout = datetime.timedelta(minutes=timeout_minutes)

    def _is_timeout(self, session):
        now = datetime.datetime.now()
        return (now - session["last_active"]) > self.timeout

    def get_session(self, user_id):
        now = datetime.datetime.now()
        session = self.sessions.get(user_id)

        if not session or self._is_timeout(session):
            session = {
                "session_id": str(uuid.uuid4()),
                "user_id": user_id,
                "start_time": now,
                "last_active": now,
                "turn_count": 0,
                "state": SessionState.STARTING,
                "emotion": ""
            }
            self.sessions[user_id] = session
            return session

        if session["turn_count"] == 0:
            session["state"] = SessionState.STARTING
        else:
            session["state"] = SessionState.CHATTING
        return session

    def update(self, user_id):
        session = self.sessions.get(user_id)
        if not session:
            return

        session["last_active"] = datetime.datetime.now()
        session["turn_count"] += 1

        # ===== 状态推进 =====
        if session["turn_count"] == 1:
            session["state"] = SessionState.CHATTING

    def end_session(self, user_id):
        session = self.sessions.get(user_id)
        if not session:
            return

        session["state"] = SessionState.IDLE