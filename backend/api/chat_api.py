import logging
from fastapi import Request, APIRouter

from services.memory_service import MemoryService
from core.exceptions import AppException
from services.auth_service import AuthService
from utils.request import extract_token_from_header
from orchestrator.chat_orchestator import ChatOrchestrator
from repositories.history_repo import HistoryRepo
from repositories.history_models import ClearUserHistoryInput


router = APIRouter(prefix="/api/chat")

@router.post("/test")
async def chat(req: Request):
    try:
        memory_svc:MemoryService = req.app.state.services["memory"]
        result=await memory_svc.fucking()
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "reply":result
            }
        }
    except AppException as e: 
        logging.info(e.message)          
        return {"code":e.code,"message":e.message,"data":None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/test_memory")
async def test_memory(req: Request, current_text: str = ""):
    """测试 get_memory 接口（GET方式）
    
    Args:
        current_text: 查询文本，用于检索相关记忆
        
    Returns:
        匹配的记忆列表
    """
    try:
        # 固定的 user_id 和 device_id
        user_id = "3f7e4b2c-8a9d-4f1e-9c2b-6a5d4e3f2a1b"
        device_id = "3f7e4b2c-8a9d-4f1e-9c2b-6a5d4e3f2a1b"
        
        # 获取 memory_service 实例
        memory_svc: MemoryService = req.app.state.services["memory"]
        
        # 调用 get_memory 方法
        memories = await memory_svc.get_memory(
            user_id=user_id,
            device_id=device_id,
            current_text=current_text,
            top_k=10
        )
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "count": len(memories),
                "memories": memories
            }
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }



@router.post("")
async def chat(req: Request):
    try:
        auth_svc:AuthService = req.app.state.services["auth"]
        token=extract_token_from_header(req)
        if token==None:
            raise AppException(500,"无token")
        user_id=await auth_svc.get_user_id_by_token(token)
        body = await req.json()
        text = body.get("input")
        chat_service:ChatOrchestrator = req.app.state.services["chat"]
        reply , debug_info = await chat_service.chat(user_id=user_id,user_input=text)
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "reply":reply,
                "debug_info": debug_info
            }
        }
    except AppException as e: 
        logging.info(e.message)          
        return {"code":e.code,"message":e.message,"data":None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/history")
async def get_chat_history(
    req: Request, 
    cursor: str = None, 
    limit: int = 20
):
    try:
        auth_svc: AuthService = req.app.state.services["auth"]
        token = extract_token_from_header(req)
        if token is None:
            raise AppException(401, "无token")
        user_id = await auth_svc.get_user_id_by_token(token)
        
        # 解析cursor为datetime
        from datetime import datetime
        cursor_datetime = None
        if cursor:
            try:
                cursor_datetime = datetime.fromisoformat(cursor)
            except ValueError:
                raise AppException(400, "cursor格式错误")
        
        chat_service: ChatOrchestrator = req.app.state.services["chat"]
        # 调用get_history_by_cursor方法
        result = await chat_service.get_history_by_cursor(
            user_id=user_id,
            cursor=cursor_datetime,
            limit=limit
        )
        
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "messages": result.items,
                "next_cursor": result.next_cursor.isoformat() if result.next_cursor else None
            }
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/clear")
async def clear_chat_history(req: Request):
    """清除用户的所有聊天记录"""
    try:
        auth_svc: AuthService = req.app.state.services["auth"]
        token = extract_token_from_header(req)
        if token is None:
            raise AppException(401, "无token")
        
        user_id = await auth_svc.get_user_id_by_token(token)
        
        # 获取 history_repo 实例
        history_repo: HistoryRepo = req.app.state.repos["history"]
        
        # 调用清除历史记录的方法
        input_data = ClearUserHistoryInput(user_id=user_id)
        result = await history_repo.clear_user_history(input_data)
        
        return {
            "code": 0,
            "message": "聊天记录清除成功",
            "data": {
                "success": result.success
            }
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.post("/update_memory")
async def update_memory(req: Request):
    """强制提取用户记忆"""
    try:
        auth_svc: AuthService = req.app.state.services["auth"]
        token = extract_token_from_header(req)
        if token is None:
            raise AppException(401, "无token")
        
        user_id = await auth_svc.get_user_id_by_token(token)
        
        # 获取 session_service 实例
        chat_orchestrator: ChatOrchestrator = req.app.state.services["chat"]
        session_service = chat_orchestrator.session_svc
        
        # 调用强制提取记忆方法
        count = await session_service.force_extract_memory(user_id)
        
        return {
            "code": 0,
            "message": "记忆提取成功",
            "data": {
                "count": count
            }
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/memory/list")
async def get_memory_list(req: Request):
    """获取用户的记忆列表"""
    try:
        auth_svc: AuthService = req.app.state.services["auth"]
        token = extract_token_from_header(req)
        if token is None:
            raise AppException(401, "无token")
        
        user_id = await auth_svc.get_user_id_by_token(token)
        
        # 获取 memory_repo 实例
        memory_repo = req.app.state.repos["memory"]
        
        # 获取用户记忆列表
        memories = await memory_repo.get_user_memories(user_id)
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": {
                "memories": memories
            }
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/memory/graph")
async def get_memory_graph(req: Request):
    """获取用户的记忆图谱数据"""
    try:
        # auth_svc: AuthService = req.app.state.services["auth"]
        # token = extract_token_from_header(req)
        # if token is None:
        #     raise AppException(401, "无token")
        
        # user_id = await auth_svc.get_user_id_by_token(token)
        
        # 获取 memory_repo 实例
        memory_repo = req.app.state.repos["memory"]
        
        # 获取用户的知识图谱数据
        graph_data = await memory_repo.get_user_graph('3f7e4b2c-8a9d-4f1e-9c2b-6a5d4e3f2a1b')
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": graph_data
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.post("/memory/delete")
async def delete_memory(req: Request):
    """删除指定记忆"""
    try:
        auth_svc: AuthService = req.app.state.services["auth"]
        token = extract_token_from_header(req)
        if token is None:
            raise AppException(401, "无token")
        
        await auth_svc.get_user_id_by_token(token)
        
        # 获取请求体中的 memory_id
        body = await req.json()
        memory_id = body.get("memory_id")
        
        if not memory_id:
            raise AppException(400, "缺少 memory_id 参数")
        
        # 获取 memory_repo 实例
        memory_repo = req.app.state.repos["memory"]
        
        # 删除记忆
        success = await memory_repo.delete_memory(memory_id)
        
        if success:
            return {
                "code": 0,
                "message": "删除成功",
                "data": None
            }
        else:
            return {
                "code": 404,
                "message": "记忆不存在或已被删除",
                "data": None
            }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.post("/tasks/extract_memory")
async def task_extract_memory(req: Request):
    """为超时会话提取记忆（供外部定时任务调用）"""
    try:
        chat_orchestrator = req.app.state.services["chat"]
        session_service = chat_orchestrator.session_svc
        
        count = await session_service.extract_memory_for_expired_sessions()
        
        return {
            "code": 0,
            "message": "记忆提取任务完成",
            "data": {
                "extracted_count": count
            }
        }
    except Exception as e:
        logging.error(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.post("/tasks/cleanup_sessions")
async def task_cleanup_sessions(req: Request):
    """清理超时会话（供外部定时任务调用）"""
    try:
        chat_orchestrator = req.app.state.services["chat"]
        session_service = chat_orchestrator.session_svc
        
        count = await session_service.cleanup_expired_sessions(timeout_minutes=60)
        
        return {
            "code": 0,
            "message": "会话清理任务完成",
            "data": {
                "cleaned_count": count
            }
        }
    except Exception as e:
        logging.error(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


def register_chat_routes(app):
    app.include_router(router)
