from fastapi import Request, APIRouter
from services.auth_service import AuthService
from models.device_model import BindDeviceRequest
from core.exceptions import AppException
from services.device_service import DeviceService
from services.ws_service import WSService
from utils.request import extract_token_from_header

import logging
router = APIRouter(prefix="/api/device")


@router.post("/bind")
async def bind_device(r:Request,request:BindDeviceRequest):
    try:
        auth_svc:AuthService = r.app.state.services["auth"]
        token=extract_token_from_header(r)
        if token==None:
            raise AppException(500,"无token")
        user_id=await auth_svc.get_user_id_by_token(token)
        device_svc:DeviceService=r.app.state.services["device"]
        device_id=request.device_id
        exists=await device_svc.validate_device_id(device_id=device_id)
        if exists==False:
            raise AppException(500,"设备id不存在")
        ifbind:bool=await device_svc.check_device_bind_info(device_id=device_id,user_id=user_id)
        if ifbind==True:
            raise AppException(500,"设备已绑定")
        status:int=await device_svc.check_device_status(device_id=device_id)
        if status==0:
            raise AppException(500,"设备离线")
        ws_svc:WSService = r.app.state.services["ws"]
        sendsuccess:bool=await ws_svc.send_to_device(device_id=device_id,message="hhhhhhhhhh")
        if sendsuccess==False:
            raise AppException(500,"发送绑定信息至设备失败")        
        ifbindsuccess:bool=await device_svc.bind_device(device_id=device_id,user_id=user_id)
        if ifbindsuccess==False:
            raise AppException(500,"绑定失败")
        return {"code":0,"message":"success","data":None}
    except Exception as e:
        logging.info(e)
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }
    except AppException as e: 
        logging.info(e.message)          
        return {"code":e.code,"message":e.message,"data":None}



def register_device_routes(app):
    app.include_router(router)
