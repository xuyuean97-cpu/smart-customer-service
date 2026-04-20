# auth/schemas.py
from pydantic import BaseModel, Field
from typing import Optional,Literal

# 发送短信
class SmsRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")

# 注册请求
class RegisterRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6, description="验证码")
    password: str = Field(..., min_length=6, description="密码")

# 登录请求 (支持 密码 或 验证码)
class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    password: Optional[str] = None # 密码登录
    code: Optional[str] = None     # 验证码登录
    login_type: Literal["password", "code"]

# 重置密码请求
class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=4, max_length=6)
    new_password: str = Field(..., min_length=6)

# 响应
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: Optional[str] = None
# 修改密码请求
class ChangePasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
