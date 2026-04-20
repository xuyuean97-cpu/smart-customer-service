# auth/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "sys_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, index=True, nullable=False, comment="手机号")
    # 新增密码字段
    hashed_password = Column(String(255), nullable=True, comment="加密密码")
    
    username = Column(String(50), nullable=True)
    nickname = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, default=datetime.now)