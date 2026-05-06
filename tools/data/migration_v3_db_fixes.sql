-- ============================================================================
-- 数据库设计补全 v3.0
-- 按优先级: P0 致命修复 → P1 Phase 2 准备 → P2 结构优化 → P3 辅助表
-- ============================================================================

-- ============================================================================
-- P0: 工单表（api/ticket.py 依赖，不创建会运行时崩溃）
-- ============================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id              VARCHAR(36) PRIMARY KEY,
    tenant_id       VARCHAR(36) NOT NULL,
    user_id         VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(36),
    status          VARCHAR(20) DEFAULT 'open',         -- open / in_progress / resolved / closed
    priority        VARCHAR(20) DEFAULT 'medium',       -- low / medium / high / urgent
    summary         VARCHAR(500) NOT NULL,
    context         TEXT,                               -- 对话上下文 JSON
    agent_id        VARCHAR(36),                        -- 分配的处理人
    resolution_note TEXT,                               -- 处理备注
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tickets_tenant_id  ON tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status     ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_agent_id   ON tickets(agent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_user_id    ON tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);

COMMENT ON TABLE tickets IS '工单表 — 人工处理流程追踪';


-- ============================================================================
-- P1: orders 表补充平台字段（Phase 2 多平台接入）
-- ============================================================================
ALTER TABLE orders ADD COLUMN IF NOT EXISTS platform           VARCHAR(20)  DEFAULT 'direct';  -- jd / taobao / pdd / douyin / direct
ALTER TABLE orders ADD COLUMN IF NOT EXISTS platform_order_id  VARCHAR(64);                   -- 平台订单号（如京东: 1234567890123456789）
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tenant_id          VARCHAR(50)  DEFAULT 'default';

-- 补齐已有的 tenant_id
UPDATE orders SET tenant_id = 'default' WHERE tenant_id IS NULL;

-- 多租户索引
CREATE INDEX IF NOT EXISTS idx_orders_tenant_id        ON orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_orders_platform         ON orders(platform);
CREATE INDEX IF NOT EXISTS idx_orders_platform_order   ON orders(platform_order_id);

COMMENT ON COLUMN orders.platform IS '订单来源: jd/taobao/pdd/douyin/direct (自营)';
COMMENT ON COLUMN orders.platform_order_id IS '平台侧订单号，与 order_id 配合做唯一去重';


-- ============================================================================
-- P1: 创建平台授权凭据表（token 续期、签名验证）
-- ============================================================================
CREATE TABLE IF NOT EXISTS platform_credentials (
    id              SERIAL PRIMARY KEY,
    tenant_id       VARCHAR(36) NOT NULL,
    platform        VARCHAR(20) NOT NULL,               -- jd / taobao / pdd / douyin
    app_key         VARCHAR(128) NOT NULL,
    app_secret      VARCHAR(256) NOT NULL,
    access_token    TEXT,
    refresh_token   TEXT,
    shop_id         VARCHAR(64),
    shop_name       VARCHAR(100),
    expires_at      TIMESTAMP,                          -- token 过期时间
    is_active       BOOLEAN DEFAULT TRUE,
    last_refreshed  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tenant_id, platform, shop_id)
);

CREATE INDEX IF NOT EXISTS idx_cred_tenant_id  ON platform_credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cred_expires    ON platform_credentials(expires_at);

COMMENT ON TABLE platform_credentials IS '多平台授权凭据 — Token 续期与签名验证';
COMMENT ON COLUMN platform_credentials.app_secret IS 'AES 加密存储，绝不以明文落盘';


-- ============================================================================
-- P2: sys_users 补充角色/邮箱字段
-- ============================================================================
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS email       VARCHAR(100);
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS role        VARCHAR(20) DEFAULT 'customer';  -- admin / agent / customer
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS preferences JSONB;

-- 把 admin 用户设为管理员
UPDATE sys_users SET role = 'admin' WHERE phone = '13800000001' AND (role IS NULL OR role = 'customer');

CREATE INDEX IF NOT EXISTS idx_users_role ON sys_users(role);

COMMENT ON COLUMN sys_users.role IS '角色: admin=系统管理员, agent=人工客服, customer=普通用户';
COMMENT ON COLUMN sys_users.preferences IS '用户偏好 JSON: {language, notification, ...}';


-- ============================================================================
-- P2: order_logistics_tracking 机场字段用视图做兼容重命名
--     不直接 RENAME COLUMN（避免 Text2SQL 训练数据和 Pydantic alias 断裂）
--     用 VIEW 对外暴露电商语义字段名
-- ============================================================================

-- 给物流表加 tenant_id 索引（已有列但无索引）
ALTER TABLE order_logistics_tracking ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'default';
UPDATE order_logistics_tracking SET tenant_id = 'default' WHERE tenant_id IS NULL;
CREATE INDEX IF NOT EXISTS idx_logistics_tenant_id ON order_logistics_tracking(tenant_id);

-- 电商语义视图：把机场字段名映射为电商名
CREATE OR REPLACE VIEW order_logistics_v AS
SELECT
    id, order_id, tracking_number, order_status, abnormal_status, abnormal_reason,
    departure_station, departure_terminal,
    scheduled_departure_time, changed_departure_time, actual_departure_time,
    destination_station, destination_terminal,
    scheduled_arrival_time, changed_arrival_time, actual_arrival_time,
    full_route_path,

    -- 电商语义别名
    airline_twocharcode   AS express_code,          -- 物流商编码
    airline_company       AS express_company,        -- 物流商名称
    aircraft_type         AS delivery_type,          -- 配送方式
    boarding_gate         AS current_station,        -- 当前配送站
    checkin_counter       AS pickup_point,           -- 揽收点
    baggage_carousel      AS self_pickup_point,      -- 自提点
    shared_flight_number  AS related_order_id,       -- 关联订单号
    airline_logo          AS express_logo,           -- 物流商 Logo

    -- 时间节点保持原名
    scheduled_cut_off_time, changed_cut_off_time, actual_cut_off_time,
    expected_security_check_duration,
    scheduled_boarding_time, changed_boarding_time, actual_boarding_time,
    scheduled_boarding_end_time, changed_boarding_end_time, actual_boarding_end_time,
    expected_boarding_walking_duration,

    subscribe_supported, last_update_time, tenant_id
FROM order_logistics_tracking;

COMMENT ON VIEW order_logistics_v IS '电商语义视图 — 将机场字段名映射为物流/电商术语，对外透明';


-- ============================================================================
-- P2: orders 加外键约束（防卫性，不加 CASCADE 防止误删）
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_orders_tenant'
    ) THEN
        ALTER TABLE orders ADD CONSTRAINT fk_orders_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_tickets_tenant'
    ) THEN
        ALTER TABLE tickets ADD CONSTRAINT fk_tickets_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_usage_tenant'
    ) THEN
        ALTER TABLE api_usage_logs ADD CONSTRAINT fk_usage_tenant
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            ON DELETE SET NULL;
    END IF;
END $$;


-- ============================================================================
-- P3: 商品信息表（RAGFlow 降级 Fallback + Text2SQL 商品查询）
-- ============================================================================
CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    spu_id          VARCHAR(50) UNIQUE NOT NULL,          -- 商品 SPU 编码
    product_name    VARCHAR(300) NOT NULL,
    category        VARCHAR(100),                         -- 商品类目
    brand           VARCHAR(100),
    base_price      DECIMAL(10,2),
    specs           JSONB DEFAULT '{}',                   -- 规格参数 JSON
    stock_status    VARCHAR(20) DEFAULT 'in_stock',       -- in_stock / low / out
    warranty        TEXT,                                 -- 保修政策
    return_policy   TEXT,                                 -- 退货政策
    description     TEXT,                                 -- 商品描述
    images          TEXT[],                               -- 商品图片 URL 数组
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_spu_id   ON products(spu_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand    ON products(brand);

COMMENT ON TABLE products IS '商品信息表 — RAGFlow 不可用时的降级数据源';


-- ============================================================================
-- P3: 审计日志表
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    tenant_id   VARCHAR(36),
    user_id     VARCHAR(50),
    action      VARCHAR(50) NOT NULL,                    -- create / update / delete / view
    resource    VARCHAR(50) NOT NULL,                    -- ticket / order / user / config
    resource_id VARCHAR(100),
    detail      JSONB,                                  -- 变更详情
    ip_address  VARCHAR(45),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant_id  ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_user_id    ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_resource   ON audit_log(resource, resource_id);

COMMENT ON TABLE audit_log IS '操作审计日志 — 合规追溯';


-- ============================================================================
-- 验证
-- ============================================================================
SELECT 'migration v3 completed' AS status;
