from fastapi import Request, APIRouter
from services.user_service import UserService
from services.auth_service import AuthService
from core.exceptions import AppException
from utils.request import extract_token_from_header
import logging
router = APIRouter(prefix="/api/user")


@router.get("/me/basic_info")
async def getMeBasicInfo(r:Request):
    try:
        auth_svc:AuthService = r.app.state.services["auth"]
        token=extract_token_from_header(r)
        if token==None:
            raise AppException(500,"无token")
        user_id=await auth_svc.get_user_id_by_token(token)

        user_svc:UserService = r.app.state.services["user"]
        result = await user_svc.get_me_basic_info(user_id)
        return {
            "code": 0,
            "message": "success",
            "data": {
                "nickname": result[0],
                "avatar_url": result[1],
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


def register_user_routes(app):
    app.include_router(router)
