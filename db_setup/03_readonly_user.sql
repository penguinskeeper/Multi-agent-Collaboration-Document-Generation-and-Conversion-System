-- ============================================================
-- 只读账号（最小权限原则）
-- 背景：tools/db_tools.py 的连接配置为 autocommit=True，
--       应用层虽有 _is_readonly_sql() 正则兜底，但数据库层再收一道权限更稳：
--       给项目专用账号只授 SELECT，即使正则被绕过也写不进去。
-- 执行方式: mysql -u root -p < 03_readonly_user.sql
--
-- ！执行前请把下面的 <CHANGE_ME> 替换为你自己设定的强密码。
--   本文件会进入公开仓库，绝不要把真实密码写进来。
--   替换后建议直接管道执行，避免改回文件后误提交：
--       mysql -u root -p < 03_readonly_user.sql
-- ============================================================

-- 项目专用只读账号（仅本地访问；localhost 与 127.0.0.1 两种连接方式都覆盖）
CREATE USER IF NOT EXISTS 'dsp_reader'@'localhost' IDENTIFIED BY '<CHANGE_ME>';
CREATE USER IF NOT EXISTS 'dsp_reader'@'127.0.0.1' IDENTIFIED BY '<CHANGE_ME>';

-- 只授业务库的查询权限，不给任何写权限
GRANT SELECT ON pharma_mall.* TO 'dsp_reader'@'localhost';
GRANT SELECT ON pharma_mall.* TO 'dsp_reader'@'127.0.0.1';

FLUSH PRIVILEGES;

-- 校验：应能看到 dsp_reader 仅持有 SELECT
SHOW GRANTS FOR 'dsp_reader'@'localhost';
SHOW GRANTS FOR 'dsp_reader'@'127.0.0.1';
