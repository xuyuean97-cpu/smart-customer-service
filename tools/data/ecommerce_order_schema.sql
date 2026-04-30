-- ============================================================================
-- 电商智能客服系统 - 订单物流数据库表结构 (PostgreSQL)
-- ============================================================================

-- 1. 订单主表
-- ============================================================================
DROP TABLE IF EXISTS orders CASCADE;
CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    order_id        VARCHAR(24)  UNIQUE NOT NULL,          -- 订单号 (如: JD2024042800001)
    user_id         VARCHAR(50)  NOT NULL,                 -- 用户ID
    product_name    VARCHAR(200) NOT NULL,                 -- 商品名称
    product_sku     VARCHAR(50),                           -- 商品SKU编码
    product_image   TEXT,                                  -- 商品图片URL
    quantity        INTEGER      DEFAULT 1,                -- 购买数量
    unit_price      DECIMAL(10,2),                         -- 单价
    total_amount    DECIMAL(10,2) NOT NULL,                -- 实付金额
    discount_amount DECIMAL(10,2) DEFAULT 0,               -- 优惠金额
    coupon_code     VARCHAR(30),                           -- 使用的优惠券码
    payment_method  VARCHAR(20),                           -- 支付方式: alipay/wechat/credit_card
    payment_status  VARCHAR(20)  DEFAULT 'pending',        -- 支付状态: pending/paid/refunding/refunded
    order_status    VARCHAR(20)  DEFAULT 'pending',        -- 订单状态: pending/paid/shipped/delivered/cancelled/returning/returned
    -- 收货人信息
    recipient_name  VARCHAR(50),                           -- 收货人姓名
    recipient_phone VARCHAR(20),                           -- 收货人电话
    shipping_address TEXT,                                 -- 收货地址
    -- 物流信息
    tracking_number VARCHAR(30),                           -- 快递单号
    express_company VARCHAR(50),                           -- 快递公司名称
    express_code    VARCHAR(10),                           -- 快递公司编码 (如: SF, YTO, ZTO)
    -- 时间节点
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- 下单时间
    paid_at         TIMESTAMP,                             -- 支付时间
    shipped_at      TIMESTAMP,                             -- 发货时间
    delivered_at    TIMESTAMP,                             -- 签收时间
    cancelled_at    TIMESTAMP,                             -- 取消时间
    -- 售后信息
    refund_status   VARCHAR(20),                           -- 退款状态: none/applying/approved/rejected/completed
    refund_amount   DECIMAL(10,2),                         -- 退款金额
    refund_reason   TEXT,                                  -- 退款原因
    -- 备注
    notes           TEXT,                                  -- 订单备注
    buyer_message   TEXT                                   -- 买家留言
);

-- 订单表索引
CREATE INDEX idx_orders_user_id    ON orders(user_id);
CREATE INDEX idx_orders_order_id   ON orders(order_id);
CREATE INDEX idx_orders_status     ON orders(order_status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_tracking   ON orders(tracking_number);


-- 2. 物流轨迹表 (字段名对齐 OrderInfo Pydantic 模型，保证前端兼容)
-- ============================================================================
DROP TABLE IF EXISTS order_logistics_tracking CASCADE;
CREATE TABLE order_logistics_tracking (
    id                      SERIAL PRIMARY KEY,
    order_id                VARCHAR(24)  NOT NULL,         -- 订单号/快递单号
    tracking_number         VARCHAR(30),                   -- 物流单号
    order_status            VARCHAR(30),                   -- 订单/物流状态 (如: 运输中/派送中/已签收)
    abnormal_status         VARCHAR(30),                   -- 异常状态
    abnormal_reason         TEXT,                          -- 异常原因

    -- 发货信息
    departure_station       VARCHAR(50),                   -- 发货地
    departure_terminal      VARCHAR(50),                   -- 发货网点
    scheduled_departure_time TIMESTAMP,                    -- 计划发货时间
    changed_departure_time   TIMESTAMP,                    -- 变更发货时间
    actual_departure_time    TIMESTAMP,                    -- 实际发货时间

    -- 收货信息
    destination_station     VARCHAR(50),                   -- 收货地
    destination_terminal    VARCHAR(50),                   -- 收货网点
    scheduled_arrival_time  TIMESTAMP,                     -- 计划到达时间
    changed_arrival_time    TIMESTAMP,                     -- 变更到达时间
    actual_arrival_time     TIMESTAMP,                     -- 实际到达时间

    -- 物流商信息
    full_route_path         TEXT,                          -- 完整运输路径
    airline_twocharcode     VARCHAR(10),                   -- 物流商代码
    airline_company         VARCHAR(50),                   -- 物流商名称
    aircraft_type           VARCHAR(20),                   -- 运输方式 (标准快递/冷链/同城配送等)

    -- 配送节点信息
    boarding_gate           VARCHAR(50),                   -- 当前配送站
    checkin_counter         VARCHAR(50),                   -- 揽收点
    baggage_carousel        VARCHAR(50),                   -- 自提点

    -- 时间节点
    scheduled_cut_off_time              TIMESTAMP,         -- 计划截单时间
    changed_cut_off_time                TIMESTAMP,         -- 变更截单时间
    actual_cut_off_time                 TIMESTAMP,         -- 实际截单时间
    expected_security_check_duration    VARCHAR(20),       -- 预计安检时长
    scheduled_boarding_time             TIMESTAMP,         -- 计划出库时间
    changed_boarding_time               TIMESTAMP,         -- 变更出库时间
    actual_boarding_time                TIMESTAMP,         -- 实际出库时间
    scheduled_boarding_end_time         TIMESTAMP,         -- 计划派送结束时间
    changed_boarding_end_time           TIMESTAMP,         -- 变更派送结束时间
    actual_boarding_end_time            TIMESTAMP,         -- 实际派送结束时间
    expected_boarding_walking_duration  VARCHAR(20),       -- 预计配送时长

    -- 其他
    shared_flight_number    VARCHAR(30),                   -- 关联订单号
    subscribe_supported     BOOLEAN DEFAULT TRUE,          -- 是否支持物流订阅
    airline_logo            TEXT,                          -- 物流商Logo (base64 data URI)

    last_update_time        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 物流轨迹表索引
CREATE INDEX idx_logistics_order_id  ON order_logistics_tracking(order_id);
CREATE INDEX idx_logistics_tracking  ON order_logistics_tracking(tracking_number);


-- 3. 快递公司Logo表
-- ============================================================================
DROP TABLE IF EXISTS express_logos CASCADE;
CREATE TABLE express_logos (
    id              SERIAL PRIMARY KEY,
    express_code    CHAR(10) UNIQUE NOT NULL,              -- 物流商编码
    express_name    VARCHAR(50),                            -- 物流商名称
    logo_data_uri   TEXT NOT NULL,                          -- Logo Data URI
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- 测试数据
-- ============================================================================

-- 快递公司Logo
INSERT INTO express_logos (express_code, express_name, logo_data_uri) VALUES
('SF',  '顺丰速运', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('YTO', '圆通速递', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('ZTO', '中通快递', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('JD',  '京东物流', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('STO', '申通快递', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('YUNDA','韵达速递','data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('DB',  '德邦快递', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...'),
('EMS', '邮政EMS',  'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0i...');

-- 测试订单数据
INSERT INTO orders (order_id, user_id, product_name, product_sku, quantity, unit_price, total_amount, discount_amount, coupon_code, payment_method, payment_status, order_status, recipient_name, recipient_phone, shipping_address, tracking_number, express_company, express_code, created_at, paid_at, shipped_at, delivered_at)
VALUES
('JD2024042800001', 'user_10001', 'iPhone 16 Pro Max 256GB 沙漠金',   'SKU-IP16PM-256-GD', 1, 9999.00,  9899.00,  100.00, 'COUPON100', 'alipay', 'paid',   'delivered', '张三', '13800001001', '广东省深圳市南山区科技园路88号', 'SF1234567890', '顺丰速运', 'SF',  '2026-04-25 10:30:00', '2026-04-25 10:31:00', '2026-04-25 15:00:00', '2026-04-27 09:15:00'),
('JD2024042800002', 'user_10001', 'Sony WH-1000XM5 无线降噪耳机 黑色', 'SKU-SONY-XM5-BK',  1, 2499.00,  2499.00,  0,      NULL,        'wechat', 'paid',   'shipped',   '张三', '13800001001', '广东省深圳市南山区科技园路88号', 'YTO9876543210', '圆通速递', 'YTO', '2026-04-27 20:15:00', '2026-04-27 20:16:00', '2026-04-28 08:30:00', NULL),
('JD2024042800003', 'user_10002', '戴森V15无绳吸尘器',                 'SKU-DYSON-V15',     1, 4990.00,  4790.00,  200.00, 'VIP200',     'alipay', 'paid',   'shipped',   '李四', '13900002002', '北京市朝阳区望京SOHO 3座1206',    'ZTO1122334455', '中通快递', 'ZTO', '2026-04-26 14:00:00', '2026-04-26 14:01:00', '2026-04-27 10:00:00', NULL),
('JD2024042800004', 'user_10003', 'Nike Air Force 1 纯白经典款 42码',  'SKU-NIKE-AF1-42',  2, 899.00,   1798.00,  0,      NULL,        'alipay', 'paid',   'pending',   '王五', '13700003003', '上海市浦东新区陆家嘴环路1000号',   NULL,             NULL,       NULL, '2026-04-28 09:00:00', '2026-04-28 09:01:00', NULL, NULL),
('JD2024042800005', 'user_10002', '安热沙小金瓶防晒霜 60ml',            'SKU-ANESSA-60ML',  1, 228.00,   228.00,   0,      NULL,        'wechat', 'paid',   'delivered', '李四', '13900002002', '北京市朝阳区望京SOHO 3座1206',    'SF5566778899', '顺丰速运', 'SF',  '2026-04-20 11:00:00', '2026-04-20 11:01:00', '2026-04-20 16:00:00', '2026-04-22 14:30:00'),
('JD2024042800006', 'user_10004', '华为MatePad Pro 12.6英寸 星空灰',    'SKU-HW-MATEPAD-GY',1, 4299.00,  4099.00,  200.00, 'NEWUSER200', 'alipay', 'paid',   'shipped',   '赵六', '13600004004', '浙江省杭州市西湖区文三路168号',    'STO9988776655', '申通快递', 'STO', '2026-04-27 16:00:00', '2026-04-27 16:01:00', '2026-04-28 07:00:00', NULL),
('JD2024042800007', 'user_10005', '良品铺子坚果大礼包 1888g',           'SKU-LPPZ-GIFT',    1, 168.00,   148.00,   20.00,  'SNACK20',    'alipay', 'paid',   'delivered', '孙七', '13500005005', '四川省成都市武侯区天府大道999号',  'JD1231231231', '京东物流', 'JD',  '2026-04-18 10:00:00', '2026-04-18 10:01:00', '2026-04-18 14:00:00', '2026-04-19 16:00:00'),
('JD2024042800008', 'user_10001', '小米Redmi K80 Pro 12GB+256GB 墨羽', 'SKU-XM-K80P-BK',   1, 3299.00,  3299.00,  0,      NULL,        'alipay', 'paid',   'returning', '张三', '13800001001', '广东省深圳市南山区科技园路88号', 'ZTO5544332211', '中通快递', 'ZTO', '2026-04-23 12:00:00', '2026-04-23 12:01:00', '2026-04-23 17:00:00', '2026-04-25 10:00:00');

-- 测试物流轨迹数据 (字段名对齐 OrderInfo)
INSERT INTO order_logistics_tracking (order_id, tracking_number, order_status, abnormal_status, abnormal_reason, departure_station, departure_terminal, scheduled_departure_time, actual_departure_time, destination_station, destination_terminal, scheduled_arrival_time, actual_arrival_time, full_route_path, airline_twocharcode, airline_company, aircraft_type, boarding_gate, checkin_counter, baggage_carousel, scheduled_cut_off_time, actual_cut_off_time, scheduled_boarding_time, actual_boarding_time, scheduled_boarding_end_time, actual_boarding_end_time, shared_flight_number, subscribe_supported)
VALUES
('JD2024042800001', 'SF1234567890', '已签收', NULL, NULL,
 '广东深圳', '深圳科技园营业部', '2026-04-25 15:00:00', '2026-04-25 15:15:00',
 '广东深圳', '深圳科技园营业部', '2026-04-27 09:00:00', '2026-04-27 09:15:00',
 '深圳科技园营业部 → 深圳转运中心 → 深圳科技园营业部', 'SF', '顺丰速运', '标准快递',
 '科技园配送站', '深圳科技园揽收点', '科技园自提柜001号',
 '2026-04-25 14:00:00', '2026-04-25 14:10:00',
 '2026-04-25 15:00:00', '2026-04-25 15:15:00',
 '2026-04-27 09:00:00', '2026-04-27 09:15:00', 'JD2024042800008', TRUE),

('JD2024042800002', 'YTO9876543210', '运输中', NULL, NULL,
 '广东深圳', '深圳南山集散中心', '2026-04-28 08:30:00', '2026-04-28 08:42:00',
 '广东深圳', '深圳科技园营业部', '2026-04-29 12:00:00', NULL,
 '深圳南山集散中心 → 广州转运中心 → 深圳科技园营业部', 'YTO', '圆通速递', '标准快递',
 '广州转运站', '深圳南山揽收点', '科技园自提柜003号',
 '2026-04-28 07:30:00', '2026-04-28 07:35:00',
 '2026-04-28 08:30:00', '2026-04-28 08:42:00',
 '2026-04-29 12:00:00', NULL, NULL, TRUE),

('JD2024042800003', 'ZTO1122334455', '派送中', NULL, NULL,
 '北京', '北京朝阳集散中心', '2026-04-27 10:00:00', '2026-04-27 10:20:00',
 '北京', '望京配送站', '2026-04-29 18:00:00', NULL,
 '北京朝阳集散中心 → 北京通州转运中心 → 望京配送站', 'ZTO', '中通快递', '标准快递',
 '望京配送站', '朝阳集散揽收点', '望京SOHO自提柜',
 '2026-04-27 09:00:00', '2026-04-27 09:05:00',
 '2026-04-27 10:00:00', '2026-04-27 10:20:00',
 '2026-04-29 18:00:00', NULL, NULL, TRUE),

('JD2024042800005', 'SF5566778899', '已签收', NULL, NULL,
 '北京', '北京望京营业部', '2026-04-20 16:00:00', '2026-04-20 16:05:00',
 '北京', '望京配送站', '2026-04-22 14:00:00', '2026-04-22 14:30:00',
 '北京望京营业部 → 北京转运中心 → 望京配送站', 'SF', '顺丰速运', '标准快递',
 '望京配送站', '北京望京揽收点', '望京SOHO自提柜',
 '2026-04-20 15:00:00', '2026-04-20 15:10:00',
 '2026-04-20 16:00:00', '2026-04-20 16:05:00',
 '2026-04-22 14:00:00', '2026-04-22 14:30:00', NULL, TRUE),

('JD2024042800006', 'STO9988776655', '运输中', NULL, NULL,
 '浙江杭州', '杭州西湖集散中心', '2026-04-28 07:00:00', '2026-04-28 07:10:00',
 '浙江杭州', '杭州文三路配送站', '2026-04-30 10:00:00', NULL,
 '杭州西湖集散中心 → 杭州转运中心 → 杭州文三路配送站', 'STO', '申通快递', '标准快递',
 '文三路配送站', '杭州西湖揽收点', '文三路自提点',
 '2026-04-28 06:00:00', '2026-04-28 06:05:00',
 '2026-04-28 07:00:00', '2026-04-28 07:10:00',
 '2026-04-30 10:00:00', NULL, NULL, TRUE),

('JD2024042800007', 'JD1231231231', '已签收', NULL, NULL,
 '四川成都', '成都高新集散中心', '2026-04-18 14:00:00', '2026-04-18 14:15:00',
 '四川成都', '成都天府配送站', '2026-04-19 16:00:00', '2026-04-19 16:00:00',
 '成都高新集散中心 → 成都转运中心 → 成都天府配送站', 'JD', '京东物流', '京准达',
 '天府配送站', '成都高新揽收点', '天府自提柜',
 '2026-04-18 13:00:00', '2026-04-18 13:10:00',
 '2026-04-18 14:00:00', '2026-04-18 14:15:00',
 '2026-04-19 16:00:00', '2026-04-19 16:00:00', NULL, TRUE),

('JD2024042800008', 'ZTO5544332211', '退货中', '退货处理', '用户申请7天无理由退货',
 '广东深圳', '深圳科技园营业部', '2026-04-23 17:00:00', '2026-04-23 17:20:00',
 '广东深圳', '深圳退货中心', '2026-04-25 10:00:00', '2026-04-25 10:00:00',
 '深圳科技园营业部 → 深圳退货中心', 'ZTO', '中通快递', '标准快递',
 '深圳退货中心', '深圳科技园揽收点', NULL,
 '2026-04-23 16:00:00', '2026-04-23 16:10:00',
 '2026-04-23 17:00:00', '2026-04-23 17:20:00',
 '2026-04-25 10:00:00', '2026-04-25 10:00:00', 'JD2024042800001', TRUE);
