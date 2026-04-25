from fastapi import Request, APIRouter, Body
from services.config_service import ConfigService
from services.auth_service import AuthService
from core.exceptions import AppException
from utils.request import extract_token_from_header
import logging
from typing import Dict, Any

router = APIRouter(prefix="/api/config")


@router.get("/ui")
async def get_ui_config(r: Request):
    try:
        auth_svc: AuthService = r.app.state.services["auth"]
        token = extract_token_from_header(r)
        if token is None:
            raise AppException(401, "无token")
        user_id = await auth_svc.get_user_id_by_token(token)

        config_svc: ConfigService = r.app.state.services["config"]
        result = await config_svc.get_ui_config(user_id)
        return {
            "code": 0,
            "message": "success",
            "data": result
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


@router.post("/user/update")
async def update_user_config(r: Request, updates: Dict[str, Any] = Body(...)):
    try:
        auth_svc: AuthService = r.app.state.services["auth"]
        token = extract_token_from_header(r)
        if token is None:
            raise AppException(401, "无token")
        user_id = await auth_svc.get_user_id_by_token(token)

        config_svc: ConfigService = r.app.state.services["config"]
        await config_svc.update_user_config(user_id, updates)
        return {
            "code": 0,
            "message": "success",
            "data": None
        }
    except Exception as e:
        print(e)
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }
    except AppException as e:
        logging.info(e.message)
        return {"code": e.code, "message": e.message, "data": None}



def register_config_routes(app):
    app.include_router(router)
