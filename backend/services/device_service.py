from dataclasses import dataclass
import os
import httpx
import uuid
import time
from core.config import config
from repositories.device_repo import BindDeviceInput, BindDeviceOutput, CheckDeviceBindInfoInput, CheckDeviceBindInfoOutput, CheckDeviceStatusInput, CheckDeviceStatusOutput, DeviceRepo, SetDeviceStatusInput, SetDeviceStatusOutput, ValidateDeviceIdInput, ValidateDeviceIdOutput
from core.exceptions import AppException
from repositories.auth_models import (
    GetOrCreateUserInput,

)
from models.auth_model import (
    WXLoginRequset,
    WXLoginResponse
)



class DeviceService:
    def __init__(self, device_repo:DeviceRepo,logger):
        self.logger = logger
        self.device_repo:DeviceRepo = device_repo
    
    async def validate_device_id(self, device_id:str) -> bool:
        output1:ValidateDeviceIdOutput=await self.device_repo.validate_device_id(ValidateDeviceIdInput(device_id=device_id))
        return output1.exists
    async def check_device_status(self,device_id:str):
        output1:CheckDeviceStatusOutput=await self.device_repo.check_device_status(CheckDeviceStatusInput(device_id=device_id))
        return output1.status
    async def set_device_status(self,device_id:str,status:int):
        output1:SetDeviceStatusOutput=await self.device_repo.set_device_status(SetDeviceStatusInput(device_id=device_id,status=status))
        return output1.success
    async def check_device_bind_info(self,device_id:str,user_id:int):
        output1:CheckDeviceBindInfoOutput=await self.device_repo.check_device_bind_info(CheckDeviceBindInfoInput(device_id=device_id,user_id=user_id))
        if output1.id=="":
            return False
        return True
    async def bind_device(self,device_id:str,user_id:int):
        output1:BindDeviceOutput=await self.device_repo.bind_device(BindDeviceInput(device_id=device_id,user_id=user_id))
        if output1.success==False:
            return False
        return True 
    
