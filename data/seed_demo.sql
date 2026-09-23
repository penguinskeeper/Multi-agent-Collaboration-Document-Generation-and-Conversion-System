-- ============================================================
-- Deep Search Pro - 医药电商演示数据（seed_demo.sql）
-- ------------------------------------------------------------
-- 用途：让项目克隆后无需外部数据库即可跑通"数据库查询助手"链路。
-- 用法：先创建好业务库（.env 中 MYSQL_DATABASE 指定的库名），
--       再执行本脚本（脚本内不指定库名，跟随当前选中数据库）：
--         mysql -u root -p your_database < data/seed_demo.sql
-- 注意：本脚本只包含演示数据，可重复执行前请先手动 DROP 旧表。
-- ============================================================

-- ---------- 1. 药品信息表 ----------
DROP TABLE IF EXISTS sales_records;
DROP TABLE IF EXISTS drugs;

CREATE TABLE drugs (
    drug_id       INT AUTO_INCREMENT PRIMARY KEY COMMENT '药品ID',
    drug_name     VARCHAR(100) NOT NULL COMMENT '药品名称',
    category      VARCHAR(50)  NOT NULL COMMENT '药品分类：处方药/非处方药/医疗器械/保健品',
    specification VARCHAR(100) NOT NULL COMMENT '规格',
    manufacturer  VARCHAR(100) NOT NULL COMMENT '生产厂家',
    unit_price    DECIMAL(10, 2) NOT NULL COMMENT '单价（元）',
    stock         INT          NOT NULL DEFAULT 0 COMMENT '库存数量',
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品信息表';

INSERT INTO drugs (drug_name, category, specification, manufacturer, unit_price, stock) VALUES
('阿莫西林胶囊',     '处方药',   '0.25g*24粒',      '华北制药',     15.80,  1200),
('布洛芬缓释胶囊',   '非处方药', '0.3g*20粒',       '中美天津史克', 22.50,  800),
('连花清瘟胶囊',     '非处方药', '0.35g*24粒',      '以岭药业',     19.90,  1500),
('左氧氟沙星片',     '处方药',   '0.5g*7片',        '浙江医药',     28.00,  350),
('氨氯地平降压片',   '处方药',   '5mg*28片',        '辉瑞制药',     45.60,  420),
('电子体温计',       '医疗器械', '软头家用款',      '欧姆龙',       89.00,  260),
('医用外科口罩',     '医疗器械', '50只/盒 独立包装','稳健医疗',     29.90,  3000),
('维生素C咀嚼片',    '保健品',   '100mg*60片',      '汤臣倍健',     68.00,  900),
('蛋白粉固体饮料',   '保健品',   '450g/罐',         '康恩贝',       158.00, 180),
('健胃消食片',       '非处方药', '0.5g*32片',       '江中药业',     12.60,  1100);

-- ---------- 2. 销售记录表 ----------
CREATE TABLE sales_records (
    record_id    INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    drug_id      INT   NOT NULL COMMENT '关联药品ID（外键 -> drugs.drug_id）',
    quantity     INT   NOT NULL COMMENT '销售数量',
    total_amount DECIMAL(12, 2) NOT NULL COMMENT '销售金额（元）= 数量 * 单价',
    sale_date    DATE  NOT NULL COMMENT '销售日期',
    channel      VARCHAR(50) NOT NULL COMMENT '销售渠道：自营商城/第三方平台/线下药店',
    CONSTRAINT fk_sales_drug FOREIGN KEY (drug_id) REFERENCES drugs (drug_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售记录表';

INSERT INTO sales_records (drug_id, quantity, total_amount, sale_date, channel) VALUES
(1, 2, 31.60,  '2026-08-28', '自营商城'),
(1, 5, 79.00,  '2026-08-28', '第三方平台'),
(2, 1, 22.50,  '2026-08-29', '线下药店'),
(2, 3, 67.50,  '2026-08-30', '自营商城'),
(3, 2, 39.80,  '2026-08-30', '第三方平台'),
(3, 8, 159.20, '2026-09-01', '自营商城'),
(4, 1, 28.00,  '2026-09-02', '线下药店'),
(5, 2, 91.20,  '2026-09-03', '自营商城'),
(5, 1, 45.60,  '2026-09-04', '第三方平台'),
(6, 1, 89.00,  '2026-09-05', '自营商城'),
(6, 2, 178.00, '2026-09-06', '线下药店'),
(7, 10, 299.00,'2026-09-06', '第三方平台'),
(7, 4, 119.60, '2026-09-07', '自营商城'),
(8, 3, 204.00, '2026-09-08', '自营商城'),
(8, 1, 68.00,  '2026-09-09', '第三方平台'),
(9, 1, 158.00, '2026-09-09', '线下药店'),
(9, 2, 316.00, '2026-09-10', '自营商城'),
(10, 4, 50.40, '2026-09-11', '线下药店'),
(10, 6, 75.60, '2026-09-12', '第三方平台'),
(1, 3, 47.40,  '2026-09-13', '线下药店'),
(3, 5, 99.50,  '2026-09-13', '自营商城'),
(2, 2, 45.00,  '2026-09-14', '自营商城'),
(7, 6, 179.40, '2026-09-14', '线下药店');
