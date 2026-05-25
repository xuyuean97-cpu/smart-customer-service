-- ============================================================================
-- 电商智能客服系统 - 数据库初始化脚本 v2.0
-- PostgreSQL 13+
-- 包含：用户认证表、多租户表、用量日志表
-- ============================================================================

-- 1. 租户表（多商户 SaaS 隔离）
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id          VARCHAR(36) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    api_key     VARCHAR(64) UNIQUE,
    config      JSONB,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE tenants IS '租户/商家表 — SaaS 多租户隔离';
COMMENT ON COLUMN tenants.api_key IS 'API Key — 用于计费和鉴权';

-- 默认租户
INSERT INTO tenants (id, name, api_key, is_active)
VALUES ('default', '默认租户', 'default-key', TRUE)
ON CONFLICT (id) DO NOTHING;


-- 2. 用户表
-- ============================================================================
CREATE TABLE IF NOT EXISTS sys_users (
    id              VARCHAR(36) PRIMARY KEY,
    phone           VARCHAR(20) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    username        VARCHAR(50),
    nickname        VARCHAR(50),
    avatar          VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- 多租户
    tenant_id       VARCHAR(36) REFERENCES tenants(id),
    -- 微信绑定
    wechat_openid   VARCHAR(100) UNIQUE,
    wechat_unionid  VARCHAR(100)
);

COMMENT ON TABLE sys_users IS '系统用户表';
COMMENT ON COLUMN sys_users.phone IS '手机号（登录账号）';
COMMENT ON COLUMN sys_users.hashed_password IS 'Argon2 哈希密码';
COMMENT ON COLUMN sys_users.wechat_openid IS '微信公众号/小程序 OpenID';
COMMENT ON COLUMN sys_users.wechat_unionid IS '微信开放平台 UnionID（跨应用统一标识）';

CREATE INDEX IF NOT EXISTS idx_users_phone ON sys_users(phone);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON sys_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_openid ON sys_users(wechat_openid);


-- 3. API 用量日志表（Token 计费）
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id          SERIAL PRIMARY KEY,
    tenant_id   VARCHAR(36),
    api_key     VARCHAR(64),
    endpoint    VARCHAR(100),
    model       VARCHAR(50),
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    success     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE api_usage_logs IS 'API 用量日志 — Token 消耗追踪';
COMMENT ON COLUMN api_usage_logs.tokens_in IS '输入 Token 数';
COMMENT ON COLUMN api_usage_logs.tokens_out IS '输出 Token 数';

CREATE INDEX IF NOT EXISTS idx_usage_tenant_id ON api_usage_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON api_usage_logs(created_at);


-- 4. 补充已有表的缺失列（sys_users / orders / order_logistics_tracking）
-- ============================================================================
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS wechat_openid VARCHAR(100) UNIQUE;
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS wechat_unionid VARCHAR(100);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'orders') THEN
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'default';
        UPDATE orders SET tenant_id = 'default' WHERE tenant_id IS NULL;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'order_logistics_tracking') THEN
        ALTER TABLE order_logistics_tracking ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'default';
        UPDATE order_logistics_tracking SET tenant_id = 'default' WHERE tenant_id IS NULL;
    END IF;
END $$;
