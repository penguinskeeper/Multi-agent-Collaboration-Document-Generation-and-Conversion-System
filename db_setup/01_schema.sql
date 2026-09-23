-- ============================================================
-- Deep Search Pro 业务库建表脚本（医药电商场景）
-- 表结构与 prompt/prompts.yml 中 sub_agents.db.description 保持一致
-- 执行方式: mysql -u root -p < 01_schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS pharma_mall
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE pharma_mall;

DROP TABLE IF EXISTS sales_records;
DROP TABLE IF EXISTS drugs;

-- ------------------------------------------------------------
-- 药品信息表
-- ------------------------------------------------------------
CREATE TABLE drugs (
    drug_id       INT PRIMARY KEY AUTO_INCREMENT COMMENT '药品ID',
    drug_name     VARCHAR(100)  NOT NULL            COMMENT '药品名称',
    category      VARCHAR(20)   NOT NULL            COMMENT '药品分类：处方药/非处方药/医疗器械/保健品',
    specification VARCHAR(100)                      COMMENT '规格',
    manufacturer  VARCHAR(100)                      COMMENT '生产厂家',
    unit_price    DECIMAL(10,2) NOT NULL            COMMENT '单价（元）',
    stock         INT           NOT NULL DEFAULT 0  COMMENT '库存数量',
    KEY idx_category (category),
    KEY idx_name (drug_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药品信息表';

-- ------------------------------------------------------------
-- 销售记录表
-- ------------------------------------------------------------
CREATE TABLE sales_records (
    record_id    INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    drug_id      INT           NOT NULL        COMMENT '关联药品ID',
    quantity     INT           NOT NULL        COMMENT '销售数量',
    total_amount DECIMAL(12,2) NOT NULL        COMMENT '销售金额（元）',
    sale_date    DATE          NOT NULL        COMMENT '销售日期',
    channel      VARCHAR(20)   NOT NULL        COMMENT '销售渠道：自营商城/第三方平台/线下药店',
    KEY idx_drug (drug_id),
    KEY idx_date (sale_date),
    KEY idx_channel (channel),
    CONSTRAINT fk_sales_drug FOREIGN KEY (drug_id) REFERENCES drugs (drug_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售记录表';
