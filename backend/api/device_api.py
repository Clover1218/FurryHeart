from fastapi import Request, APIRouter
from services.auth_service import AuthService
from models.device_model import BindDeviceRequest
from core.exceptions import AppException
from services.device_service import DeviceService
from utils.request import extract_token_from_header

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device")


@router.post("/bind")
async def bind_device(r: Request, request: BindDeviceRequest):
    """小程序端发起绑定请求

    流程:
    1. 验证用户登录态
    2. 检查设备存在、未绑定、在线
    3. 生成绑定 token 存入 Redis
    4. 返回 token 给小程序端，由小程序通过蓝牙写入硬件
    """
    try:
        auth_svc: AuthService = r.app.state.services["auth"]
        device_svc: DeviceService = r.app.state.services["device"]

        token = extract_token_from_header(r)
        if token is None:
            raise AppException(401, "未登录")
        user_id = await auth_svc.get_user_id_by_token(token)
        if not user_id:
            raise AppException(401, "登录已过期")

        device_id = request.device_id

        exists = await device_svc.verify_device_id(device_id)
        if not exists:
            raise AppException(404, "设备不存在")

        bound_user_id = await device_svc.get_device_bind_info(device_id)
        if bound_user_id:
            raise AppException(409, "设备已绑定")

        status = await device_svc.get_device_status(device_id)
        if status != 'active':
            raise AppException(400, "设备离线，请确保设备已联网")

        bind_token = await device_svc.create_bind_token(device_id, user_id)
        if not bind_token:
            raise AppException(500, "创建绑定令牌失败，请稍后重试")

        return {"code": 0, "message": "success", "data": {"token": bind_token}}

    except AppException as e:
        logger.info(f"绑定设备失败: {e.message}")
        return {"code": e.code, "message": e.message, "data": None}


@router.post("/unbind")
async def unbind_device(r: Request, request: BindDeviceRequest):
    """小程序端发起解绑请求

    流程:
    1. 验证用户登录态
    2. 检查设备存在且已绑定到当前用户、在线
    3. 生成解绑 token 存入 Redis
    4. 返回 token 给小程序端，由小程序通过蓝牙写入硬件
    """
    try:
        auth_svc: AuthService = r.app.state.services["auth"]
        device_svc: DeviceService = r.app.state.services["device"]

        token = extract_token_from_header(r)
        if token is None:
            raise AppException(401, "未登录")
        user_id = await auth_svc.get_user_id_by_token(token)
        if not user_id:
            raise AppException(401, "登录已过期")

        device_id = request.device_id

        exists = await device_svc.verify_device_id(device_id)
        if not exists:
            raise AppException(404, "设备不存在")

        bound_user_id = await device_svc.get_device_bind_info(device_id)
        if not bound_user_id:
            raise AppException(409, "设备未绑定")

        if bound_user_id != user_id:
            raise AppException(403, "无权解绑此设备")

        status = await device_svc.get_device_status(device_id)
        if status != 'active':
            raise AppException(400, "设备离线，请确保设备已联网")

        unbind_token = await device_svc.create_unbind_token(device_id, user_id)
        if not unbind_token:
            raise AppException(500, "创建解绑令牌失败，请稍后重试")

        return {"code": 0, "message": "success", "data": {"token": unbind_token}}

    except AppException as e:
        logger.info(f"解绑设备失败: {e.message}")
        return {"code": e.code, "message": e.message, "data": None}


def register_device_routes(app):
    app.include_router(router)
