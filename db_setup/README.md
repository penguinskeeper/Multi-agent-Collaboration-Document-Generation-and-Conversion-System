# 数据库环境搭建说明（本地 MySQL 8.4）

本目录是「数据库查询助手」的配套环境脚本。表结构严格对齐 `prompt/prompts.yml` 中
`sub_agents.db.description` 里声明的 schema。

> **先看这里——本项目有两条数据库路线，别混用**
>
> | 路线 | 建库脚本 | 库名 | 数据量 | 适用场景 |
> |---|---|---|---|---|
> | **A. Docker 一键**（推荐新手） | `data/seed_demo.sql` | `pharma_demo` | 10 种药品 | `docker compose up -d` 自动导入，走 README 主线 |
> | **B. 本机手工部署**（本目录） | `01_schema.sql` + `02_seed.sql` | `pharma_mall` | 40 种药品 / 240 条销售记录 | 想跑更真实的数据体量，或不用 Docker |
>
> 两条路线的表结构（`drugs` / `sales_records`）一致，差别只在数据量与库名。
> **选一条走完即可**：两条都导会得到两个库，而 `.env` 里的 `MYSQL_DATABASE` 只有一个值，
> Agent 会连错库。走本目录这条路线时，把 `.env` 的 `MYSQL_DATABASE` 设为 `pharma_mall`。

## 一、参考部署参数（示例值，请按你的环境调整）

| 项 | 值 |
|---|---|
| MySQL 版本 | 8.4.6 LTS（ZIP 免安装版） |
| 程序目录 | `<MYSQL_HOME>\mysql-8.4.6-winx64` |
| 数据目录 | `<MYSQL_HOME>\data` |
| 配置文件 | `<MYSQL_HOME>\my.ini` |
| 端口 | 3306 |
| 业务库 | `pharma_mall`（40 种药品 / 240 条销售记录） |
| root 密码 | 安装时自行设置，**不要写进仓库** |
| 应用账号 | `dsp_reader`（**只授 SELECT**，最小权限）；密码在执行 `03_readonly_user.sql` 前自行填入 |

## 二、日常启停

```bat
<MYSQL_HOME>\start_mysql.bat     :: 前台启动（窗口保持打开）
<MYSQL_HOME>\stop_mysql.bat      :: 优雅关闭（会提示输入 root 密码）
```

想让 MySQL 开机自启、无需手动开窗口：右键 `<MYSQL_HOME>\install_service_admin.bat`
→ **以管理员身份运行**，注册为 Windows 服务 `MySQL84`。

## 三、从零重建（换机器时）

```bat
:: 1. 下载 MySQL 8.4 LTS ZIP（约 249MB）
::    https://dev.mysql.com/get/Downloads/MySQL-8.4/mysql-8.4.6-winx64.zip
:: 2. 解压到 <MYSQL_HOME>\，复制 my.ini.example 为 <MYSQL_HOME>\my.ini
::    并把文件里的 <MYSQL_HOME> 占位符替换为你的实际路径
:: 3. 初始化数据目录（生成空密码 root）
<MYSQL_HOME>\mysql-8.4.6-winx64\bin\mysqld.exe --defaults-file="<MYSQL_HOME>\my.ini" --initialize-insecure --console
:: 4. 启动服务
<MYSQL_HOME>\start_mysql.bat
:: 5. 建库 + 灌数据 + 建只读账号（按顺序执行）
<MYSQL_HOME>\mysql-8.4.6-winx64\bin\mysql.exe -u root --host=127.0.0.1 < 01_schema.sql
python gen_seed.py
<MYSQL_HOME>\mysql-8.4.6-winx64\bin\mysql.exe -u root --host=127.0.0.1 < 02_seed.sql
<MYSQL_HOME>\mysql-8.4.6-winx64\bin\mysql.exe -u root --host=127.0.0.1 < 03_readonly_user.sql
:: 6. 设置 root 密码（自行设定强密码；切勿把真实密码提交进仓库）
::    ALTER USER 'root'@'localhost' IDENTIFIED BY '<CHANGE_ME>';
```

## 四、文件说明

| 文件 | 用途 |
|---|---|
| `01_schema.sql` | 建库 `pharma_mall` + 建表 `drugs` / `sales_records` |
| `gen_seed.py` | 生成样例数据 SQL（随机但种子固定，结果可复现） |
| `02_seed.sql` | 由 `gen_seed.py` 生成的数据（40 药品 / 240 销售记录，2026-06-01 ~ 2026-09-15） |
| `03_readonly_user.sql` | 建只读账号 `dsp_reader`（仅 SELECT 权限） |
| `my.ini.example` | MySQL 配置模板（含 `innodb_buffer_pool_size=256M`，适配 8GB 内存开发机；使用时替换 `<MYSQL_HOME>` 占位符） |
| `test_db_tools_live.py` | 三个数据库工具的连通性 + 安全拦截验证脚本 |
| `e2e_db_test.py` | 端到端验证：提交任务 → WebSocket 接收智能体实时结果 |

## 五、已知坑

1. **必须设置 `use_pure=True`**：`mysql-connector-python` 9.x 的 C 扩展在部分 Python 3.13
   环境下建立连接时会直接段错误（进程崩溃、无法被 try/except 捕获）。
   `tools/db_tools.py` 的 `get_db_config()` 已强制纯 Python 模式。
2. **`.env` 路径加载**：`tools/db_tools.py` 与 `rawflow/rag_config.py` 均已改为基于
   文件位置定位项目根 `.env`，不再依赖当前工作目录。
3. **只读账号是最稳的一道防线**：SQL 只读校验在应用层（正则），数据库层再叠加
   只授 SELECT 的账号，双保险。
