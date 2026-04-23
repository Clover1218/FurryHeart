import logging
from fastapi import Request, APIRouter

from core.exceptions import AppException
from services.auth_service import AuthService
from utils.request import extract_token_from_header
from orchestrator.chat_orchestator import ChatOrchestrator


router = APIRouter(prefix="/api/chat")


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
        reply = await chat_service.chat(user_id=user_id,user_input=text)
        return {
            "code": 0,
            "message": "ok",
            "data": {
                "reply":reply
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


def register_chat_routes(app):
    app.include_router(router)
