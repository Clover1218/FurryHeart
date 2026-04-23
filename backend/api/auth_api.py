from fastapi import Request, APIRouter
from services.auth_service import AuthService
from models.auth_model import WXLoginRequset,LoginRequset
from core.exceptions import AppException

import logging
router = APIRouter(prefix="/api/auth")


@router.post("/wx_login")
async def wx_login(r:Request,req: WXLoginRequset):
    code = req.code
    try:
        auth_svc:AuthService = r.app.state.services["auth"]
        result = await auth_svc.wechat_login(WXLoginRequset(code=code))
        return {
            "code": 0,
            "message": "success",
            "data": result
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
@router.post("/login")
async def login(r:Request,req: LoginRequset):
    open_id = req.open_id
    try:
        auth_svc:AuthService = r.app.state.services["auth"]
        result = await auth_svc.login(open_id)
        return {
            "code": 0,
            "message": "success",
            "data": {"token":result}
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

def register_auth_routes(app):
    app.include_router(router)
