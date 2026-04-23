from pydantic import BaseModel, Field, EmailStr




class BindDeviceRequest(BaseModel):
    device_id : str=...
class BindDeviceResponse(BaseModel):
    token: str=...