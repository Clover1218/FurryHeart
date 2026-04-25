import os

from api.device_api import register_device_routes
from api.ws_api import register_ws_routes
from api.config_api import register_config_routes
from core.config import config
from core.ws_manager import WSManager
from repositories.device_repo import DeviceRepo
from repositories.config_repo import ConfigRepo
from services.device_service import DeviceService
from services.config_service import ConfigService
from services.llm.deepseek_client import DeepSeekClient
from services.ws_service import WSService

# 设置 HuggingFace 镜像
os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")

from fastapi import FastAPI
from contextlib import asynccontextmanager

import uvicorn

from core.db import create_pool,create_redis_client
from core.logger import create_logger

from repositories.memory_repo import MemoryRepo
from repositories.auth_repo import AuthRepo
from repositories.user_repo import UserRepo
from repositories.history_repo import HistoryRepo

from services.session_service import SessionService
from services.emotion_service import EmotionService
from services.history_service import HistoryService
from services.llm_service import LLMService
from services.memory_service import MemoryService
from services.embedding_service import EmbeddingService
from services.llm.iflow_client import iFlowClient
from services.auth_service import AuthService
from services.user_service import UserService
from orchestrator.chat_orchestator import ChatOrchestrator

from api.chat_api import register_chat_routes
from api.auth_api import register_auth_routes
from api.user_api import register_user_routes



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = create_logger()
    logger.info("启动服务")

    db_pool = await create_pool()
    redis_client= await create_redis_client()
    ws_manager = WSManager()
    auth_repo = AuthRepo(db_pool=db_pool,redis_client=redis_client)
    user_repo = UserRepo(db_pool=db_pool)
    device_repo = DeviceRepo(db_pool=db_pool,redis_client=redis_client)
    memory_repo = MemoryRepo(db_pool,logger)
    history_repo = HistoryRepo(db_pool, logger)
    config_repo = ConfigRepo(db_pool)
    iFlow_client=iFlowClient()
    DeepSeek_client=DeepSeekClient()
    llm_service=LLMService(DeepSeek_client,logger)
    session_service= SessionService()
    emotion_service= EmotionService(llm_service,logger)
    history_service= HistoryService(history_repo,logger)
    embedding_service= EmbeddingService(logger)
    memory_service = MemoryService(memory_repo,embedding_service,llm_service,logger)
    config_service = ConfigService(config_repo)
    chat = ChatOrchestrator(session_service,emotion_service,history_service,memory_service,llm_service,config_service,logger)

    auth_service = AuthService(auth_repo,logger)
    user_service = UserService(user_repo,logger)
    device_service = DeviceService(device_repo,logger)

    ws_service = WSService(ws_manager=ws_manager,device_service=device_service)
    app.state.services = {
        "chat": chat,
        "auth": auth_service,
        "user": user_service,
        "device": device_service,
        "config": config_service,
        "ws": ws_service
    }
    app.state.logger = logger
    yield

    await db_pool.close()
    logger.info("服务关闭")


app = FastAPI(lifespan=lifespan)

register_chat_routes(app)
register_auth_routes(app)
register_user_routes(app)
register_config_routes(app)
register_ws_routes(app)
register_device_routes(app)
uvicorn.run(app, host=config.server.host, port=config.server.port)
