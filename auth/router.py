# auth/router.py
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from auth.sms import send_ali_sms
from . import schemas, redis_client, models, security
from .database import get_db
from .config import settings

router = APIRouter(prefix="/api/auth", tags=["用户认证"])

# 1. 发送短信
@router.post("/send-sms", summary="发送短信验证码")
async def send_sms(req: schemas.SmsRequest):
    # 1. 【新增】检查冷却时间
    if redis_client.check_sms_cooldown(req.phone):
        raise HTTPException(
            status_code=429, # Too Many Requests
            detail="短信发送过于频繁，请 60 秒后再试"
        )

    # 2. 生成随机码
    code = str(random.randint(100000, 999999))
    
    # 3. 存入 Redis (验证码本身)
    redis_client.set_sms_code(req.phone, code)
    
    # 4. 发送真实短信
    # 如果你是开发环境不想浪费短信条数，可以在这里加个 if 判断跳过
    is_sent = await send_ali_sms(req.phone, code)
    
    if is_sent:
        # 5. 【新增】发送成功后，写入冷却标记 (60秒)
        redis_client.set_sms_cooldown(req.phone, 60)
        
        return {"code": 200, "message": "短信发送成功", "debug_code": code}
    else:
        # 发送失败通常不需要冷却，允许用户立即重试，或者设置一个较短的冷却(如5秒)防止死循环
        # 这里演示不设置冷却
        print(f"======> [模拟短信(发送失败转模拟)] 手机号: {req.phone}, 验证码: {code} <======")
        return {"code": 200, "message": "短信发送请求已处理(开发模式模拟成功)", "debug_code": code}

# 2. 用户注册
@router.post("/register", summary="新用户注册")
async def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    # A. 校验验证码
    cached_code = redis_client.get_sms_code(req.phone)
    if not cached_code or cached_code != req.code:
        raise HTTPException(status_code=400, detail="验证码错误或已失效")
    
    # B. 检查手机号是否已存在
    if db.query(models.User).filter(models.User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")
    
    # C. 创建用户
    print("password repr:", repr(req.password))
    print("password bytes len:", len(req.password.encode("utf-8")))
    hashed_pwd = security.get_password_hash(req.password)
    new_user = models.User(
        phone=req.phone,
        hashed_password=hashed_pwd,
        username=f"用户{req.phone[-4:]}",
        nickname="新用户"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # D. 注册成功后销毁验证码
    redis_client.delete_sms_code(req.phone)
    
    return {"code": 200, "message": "注册成功", "user_id": new_user.id}

@router.post("/login", response_model=schemas.TokenResponse, summary="登录")
async def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=401, detail="账号或凭证错误")

    # =====================
    # 密码登录
    # =====================
    if req.login_type == "password":
        if not req.password:
            raise HTTPException(status_code=400, detail="请输入密码")

        if not user.hashed_password:
            raise HTTPException(status_code=400, detail="该账号未设置密码")

        if not security.verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="账号或凭证错误")

    # =====================
    # 验证码登录
    # =====================
    elif req.login_type == "code":
        if not req.code:
            raise HTTPException(status_code=400, detail="请输入验证码")

        cached_code = redis_client.get_sms_code(req.phone)
        if not cached_code or cached_code != req.code:
            raise HTTPException(status_code=401, detail="账号或凭证错误")

        redis_client.delete_sms_code(req.phone)

    else:
        raise HTTPException(status_code=400, detail="非法登录方式")

    # =====================
    # 登录成功处理
    # =====================
    user.last_login = datetime.utcnow()
    db.commit()

    token = security.create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
    }


# 4. 忘记密码 / 重置密码
@router.post("/reset-password", summary="找回密码")
async def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # A. 校验验证码
    cached_code = redis_client.get_sms_code(req.phone)
    if not cached_code or cached_code != req.code:
        raise HTTPException(status_code=400, detail="验证码错误或失效")
        
    # B. 查找用户
    user = db.query(models.User).filter(models.User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
        
    # C. 更新密码
    user.hashed_password = security.get_password_hash(req.new_password)
    db.commit()
    
    redis_client.delete_sms_code(req.phone)
    
    return {"code": 200, "message": "密码重置成功，请重新登录"}

@router.post("/change-password", summary="修改密码（需登录）")
async def change_password(
    req: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    # A. 校验旧密码
    if not security.verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    # B. 防止新旧密码相同
    if req.old_password == req.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与旧密码相同")

    # C. 更新密码
    current_user.hashed_password = security.get_password_hash(req.new_password)
    db.commit()

    return {"code": 200, "message": "密码修改成功，请重新登录"}