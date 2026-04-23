from fastapi import Request, APIRouter, WebSocket, WebSocketDisconnect
from services.device_service import DeviceService
from services.user_service import UserService
from services.auth_service import AuthService
from core.exceptions import AppException
from services.ws_service import WSService
from utils.request import extract_token_from_header
import logging

router = APIRouter(prefix="/api")


@router.websocket("/ws/{device_id}")
async def handle_ws_device(websocket: WebSocket, device_id: str):
    """处理设备 WebSocket 连接"""
    try:
        # 验证设备 ID
        device_svc: DeviceService = websocket.app.state.services["device"]
        exists = await device_svc.validate_device_id(device_id=device_id)
        if not exists:
            await websocket.close(code=1008, reason="设备不存在")
            return
        
        # 接受连接
        await websocket.accept()
        
        # 处理连接
        ws_svc: WSService = websocket.app.state.services["ws"]
        await ws_svc.handle_connection(websocket=websocket, device_id=device_id)
        
    except WebSocketDisconnect:
        logging.info(f"设备 {device_id} WebSocket 连接断开")
    except Exception as e:
        logging.error(f"WebSocket 处理错误: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


def register_ws_routes(app):
    app.include_router(router)
