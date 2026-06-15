import os

from langchain_deepseek import ChatDeepSeek

from api.device_api import register_device_routes
from api.ws_api import register_ws_routes
from api.config_api import register_config_routes

from services.tts_service import TTSService
from services.asr_service import ASRService
from core.config import ASR_MODEL, DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, SAMPLE_RATE, TTS_MODEL, TTS_VOICE, config
from services.scene_service import SceneService
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

import logging

from core.db import create_pool,create_redis_client
from core.logger import setup_logging

from repositories.memory_repo import MemoryRepo
from repositories.auth_repo import AuthRepo
from repositories.user_repo import UserRepo
from repositories.history_repo import HistoryRepo
from repositories.session_repo import SessionRepo

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
from orchestrator.chat_agent import ChatAgent

from api.chat_api import register_chat_routes, scheduled_task_extract_memory
from api.auth_api import register_auth_routes
from api.user_api import register_user_routes
from core.scheduler import add_hourly_task, add_interval_task, start_scheduler, shutdown_scheduler
from dotenv import load_dotenv
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化日志系统（必须先于其他操作）
    setup_logging(
        log_dir=config.log.dir,
        log_level=getattr(logging, config.log.level.upper(), logging.INFO),
        console_level=getattr(logging, config.log.console_level.upper(), logging.WARNING),
    )
    logger = logging.getLogger("heartbot")
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
    session_repo = SessionRepo(db_pool, logger)
    iFlow_client=iFlowClient()
    DeepSeek_client=DeepSeekClient(api_key=DEEPSEEK_API_KEY)
    asr_service=ASRService(SAMPLE_RATE,ASR_MODEL,DASHSCOPE_API_KEY)
    tts_service=TTSService(TTS_MODEL,TTS_VOICE,DASHSCOPE_API_KEY)
    llm_service=LLMService(DeepSeek_client,logger)
    session_service = SessionService(
        session_repo=session_repo,
        logger=logger,
        timeout_minutes=5,
        memory_threshold_minutes=30
    )
    emotion_service = EmotionService(llm_service, logger)
    history_service = HistoryService(history_repo, logger)
    embedding_service = EmbeddingService(logger)
    scene_service = SceneService(llm_service, logger)
    memory_service = MemoryService(memory_repo, embedding_service, llm_service, logger)
    config_service = ConfigService(config_repo)
    
    # 设置 SessionService 的依赖
    session_service.set_dependencies(memory_service, history_service)
    
    chat = ChatOrchestrator(session_service, emotion_service, history_service, memory_service, scene_service, llm_service, config_service, logger)
    model = ChatDeepSeek(
        model="deepseek-v4-flash", 
        temperature=0.7       
    )
    chat_agent = ChatAgent(session_service, emotion_service, history_service, memory_service, scene_service, llm_service, config_service, model,logger)
    auth_service = AuthService(auth_repo,logger)
    user_service = UserService(user_repo,logger)
    device_service = DeviceService(device_repo,logger)

    ws_service = WSService(ws_manager=ws_manager,device_service=device_service,asr_service=asr_service,tts_service=tts_service,chat_orchestrator=chat)
    app.state.services = {
        "chat": chat,
        "auth": auth_service,
        "user": user_service,
        "device": device_service,
        "config": config_service,
        "ws": ws_service,
        "memory": memory_service,
        "chat_agent": chat_agent
    }
    app.state.repos = {
        "history": history_repo,
        "memory": memory_repo,
        "auth": auth_repo,
        "user": user_repo,
        "device": device_repo,
        "config": config_repo
    }
    app.state.logger = logger

    async def scheduled_extract_memory_task():
        """每小时执行的记忆检索任务"""

        await scheduled_task_extract_memory(chat)

    add_hourly_task("memory_test_task", scheduled_extract_memory_task)
    # def gua():
    #     logger.info("呱呱呱")
    # add_interval_task("gua",gua,1)
    start_scheduler()
    logger.info("定时任务调度器已启动")

    yield

    shutdown_scheduler()
    await db_pool.close()
    logger.info("服务关闭")


app = FastAPI(lifespan=lifespan)

register_chat_routes(app)
register_auth_routes(app)
register_user_routes(app)
register_config_routes(app)
register_ws_routes(app)
register_device_routes(app)

if __name__ == "__main__":
    uvicorn.run(app, host=config.server.host, port=config.server.port)
