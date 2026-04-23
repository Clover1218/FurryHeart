from dataclasses import dataclass
import os
import httpx
import uuid
import time
from core.config import config
from repositories.auth_repo import AuthRepo
from core.exceptions import AppException
from repositories.auth_models import (
    GetOrCreateUserInput,
    GetOrCreateUserOutput,
    GetUserInput,
    GetUserOutput,
    SaveTokenInput,
    SaveTokenOutput,
    GetTokenInput,
    GetTokenOutput,
)
from models.auth_model import (
    WXLoginRequset,
    WXLoginResponse
)



class AuthService:
    
    def __init__(self, auth_repo:AuthRepo,logger):
        self.logger = logger
        self.auth_repo:AuthRepo = auth_repo
    
    async def wechat_login(self, input_data: WXLoginRequset) -> WXLoginResponse:
        """微信登录
        
        Args:
            input_data: 包含微信小程序登录 code 的输入
            
        Returns:
            WechatLoginOutput: 包含 open_id 和 token 的响应数据
        """
        # 获取微信配置
        appid = os.getenv("WX_APPID", "")
        secret = os.getenv("WX_SECRET", "")
        
        if not appid or not secret:
            raise Exception("微信配置缺失")
        
        # 调用微信 code2session 接口
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": appid,
            "secret": secret,
            "js_code": input_data.code,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise Exception(f"微信接口调用失败: {str(e)}")
        
        # 检查微信返回结果
        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"微信登录失败: {data.get('errmsg', '未知错误')}")
        
        openid = data.get("openid")
        if not openid:
            raise Exception("微信返回数据异常")
        
        # 处理用户（查询或创建）
        output: GetOrCreateUserOutput = await self.auth_repo.get_or_create_user(
            GetOrCreateUserInput(open_id=openid)
        )
        output1:SaveTokenOutput=await self.auth_repo.save_token(SaveTokenInput(user_id=output.user_id))
        
        return WXLoginResponse(
            open_id=output.user_id,
            token=output1.token
        )
    async def get_user_id_by_token(self,token:str)-> str:
        output:GetTokenOutput=await self.auth_repo.get_token(GetTokenInput(token=token))
        if output.exist==False:
            raise AppException(message="无效token",code=500)
        return output.user_id
    async def login(self, open_id) -> str:
        output: GetUserOutput = await self.auth_repo.get_user(
            GetUserInput(open_id=open_id)
        )
        if output.exist==False:
            raise AppException(message="用户不存在", code=500)
        output1:SaveTokenOutput=await self.auth_repo.save_token(SaveTokenInput(user_id=output.user_id))
        
        return output1.token
