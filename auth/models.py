# auth/models.py
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Tenant(Base):
    """租户/商家模型 — SaaS 多租户隔离"""
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, comment="租户名称")
    api_key = Column(String(64), unique=True, index=True, comment="API Key（用于计费验证）")
    config = Column(JSON, nullable=True, comment="租户自定义配置")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now)

    users = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "sys_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, index=True, nullable=False, comment="手机号")
    hashed_password = Column(String(255), nullable=True, comment="加密密码")

    username = Column(String(50), nullable=True)
    nickname = Column(String(50), nullable=True)
    avatar = Column(String(255), nullable=True)
    role = Column(String(20), default="customer", comment="角色: admin/agent/customer")
    email = Column(String(100), nullable=True, comment="邮箱")
    preferences = Column(JSON, nullable=True, comment="用户偏好")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, default=datetime.now)

    # 多租户
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, default=None, comment="所属租户")
    tenant = relationship("Tenant", back_populates="users")

    # 微信绑定
    wechat_openid = Column(String(100), unique=True, nullable=True, comment="微信 OpenID")
    wechat_unionid = Column(String(100), nullable=True, comment="微信 UnionID")


class UsageLog(Base):
    """API 用量日志 — Token 计费"""
    __tablename__ = "api_usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), index=True, comment="租户ID")
    api_key = Column(String(64), comment="使用的 API Key")
    endpoint = Column(String(100), comment="调用的端点")
    model = Column(String(50), comment="使用的模型")
    tokens_in = Column(Integer, default=0, comment="输入 token 数")
    tokens_out = Column(Integer, default=0, comment="输出 token 数")
    success = Column(Boolean, default=True, comment="是否成功")
    created_at = Column(DateTime, default=datetime.now)
