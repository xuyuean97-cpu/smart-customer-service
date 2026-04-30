-- ============================================================================
-- Phase 1 多租户迁移脚本 v2.0
-- 给现有表添加 tenant_id 列，支持 SaaS 多商户隔离
-- ============================================================================

-- 1. 创建租户表
-- ============================================================================
CREATE TABLE IF NOT EXISTS tenants (
    id          VARCHAR(36) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    api_key     VARCHAR(64) UNIQUE,
    config      JSONB,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认租户
INSERT INTO tenants (id, name, api_key, is_active)
VALUES ('default', '默认租户', 'default-key', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 2. 订单表添加 tenant_id
-- ============================================================================
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'default';
UPDATE orders SET tenant_id = 'default' WHERE tenant_id IS NULL;

-- 3. 物流轨迹表添加 tenant_id
-- ============================================================================
ALTER TABLE order_logistics_tracking ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'default';
UPDATE order_logistics_tracking SET tenant_id = 'default' WHERE tenant_id IS NULL;

-- 4. 用户表添加 tenant_id 外键 + 微信字段
-- ============================================================================
-- tenant_id (如果 sys_users 表已存在)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sys_users') THEN
        ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(36) REFERENCES tenants(id);
        ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS wechat_openid VARCHAR(100);
        ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS wechat_unionid VARCHAR(100);
    END IF;
END $$;

-- 5. 创建 API 用量日志表
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

CREATE INDEX IF NOT EXISTS idx_usage_tenant_id ON api_usage_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON api_usage_logs(created_at);
