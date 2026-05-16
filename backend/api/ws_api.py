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
    """处理设备 WebSocket 连接
    
    连接流程：
    1. 检查设备 ID 是否存在于数据库中
    2. 设备存在则接受连接，更新设备状态为 active
    3. 设备不存在则拒绝连接
    4. 连接断开时更新设备状态为 offline
    """
    try:
        # 获取设备服务
        device_svc: DeviceService = websocket.app.state.services["device"]
        
        # 1. 检查设备 ID 是否存在
        exists = await device_svc.verify_device_id(device_id)
        if not exists:
            logging.warning(f"设备 {device_id} 不存在，拒绝 WebSocket 连接")
            await websocket.close(code=1008, reason="设备不存在")
            return
        
        # 2. 接受连接并更新设备状态为 active
        await websocket.accept()
        logging.info(f"设备 {device_id} WebSocket 连接成功，状态已更新为 active")
        
        # 3. 处理连接
        ws_svc: WSService = websocket.app.state.services["ws"]
        await ws_svc.handle_connection(websocket=websocket, device_id=device_id)
        
    except WebSocketDisconnect:
        # 4. 连接断开时更新设备状态为 offline
        try:
            await device_svc.update_device_status(device_id, 'offline')
            logging.info(f"设备 {device_id} WebSocket 连接断开，状态已更新为 offline")
        except Exception as e:
            logging.error(f"更新设备 {device_id} 断开状态失败: {e}")
    except Exception as e:
        logging.error(f"WebSocket 处理错误: {e}")
        try:
            # 发生错误时也更新状态为 offline
            await device_svc.update_device_status(device_id, 'offline')
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


def register_ws_routes(app):
    app.include_router(router)
