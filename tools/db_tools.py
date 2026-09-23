import os
import re
import logging
from pathlib import Path
from dotenv import load_dotenv
from api.monitor import monitor
from mysql.connector import connect, Error
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# ---------------------------- 只读安全防护 ----------------------------
# 连接配置为 autocommit=True，任何写语句都会立即生效。
# 该工具面向 LLM（可能幻觉 / 被 prompt 注入），必须强制只读：
# 仅允许 SELECT / SHOW / DESC(RIBE) / EXPLAIN，且禁止多语句与注释包裹绕过。
_READONLY_SQL_PATTERN = re.compile(r"^\s*(select|show|describe|desc|explain)\b", re.IGNORECASE)
# 表名/标识符白名单：字母、数字、下划线、$（先剥掉反引号/双引号）
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_$]+$")


def _is_readonly_sql(query: str) -> bool:
    """校验 SQL 是否为安全的单条只读查询。"""
    q = (query or "").strip().rstrip(";")
    # 去掉行注释与块注释，防止用注释伪装出 SELECT 前缀绕过校验
    q = re.sub(r"--.*?$|/\*.*?\*/", " ", q, flags=re.DOTALL | re.MULTILINE).strip()
    if not q or ";" in q:
        return False
    return bool(_READONLY_SQL_PATTERN.match(q))


def _is_safe_identifier(table_name: str) -> bool:
    """校验表名是否为无注入风险的合法标识符。"""
    name = str(table_name or "").strip().strip("`\"'").strip()
    return bool(_IDENTIFIER_PATTERN.match(name))

# 显式从项目根 .env 加载配置，避免依赖当前工作目录（CWD）
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")


# 加载配置文件方便后续使用
def get_db_config():
    """Get database configuration from environment variables."""
    config = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True,
        # 强制走纯 Python 实现：mysql-connector-python 9.x 自带的 C 扩展
        # 在部分 Python 3.13 环境下建立连接时直接段错误（进程崩溃、无异常可捕），
        # 纯 Python 模式功能等价且稳定，连接开销对本场景可忽略。
        "use_pure": True,
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL")
    }
    # 移除 None 值（核心必要操作）
    config = {k: v for k, v in config.items() if v is not None}

    # 补充：校验核心配置是否存在（可选但推荐）
    required_keys = ["user", "password", "database"]
    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        raise ValueError(f"缺失数据库核心配置：{', '.join(missing_keys)}")

    return config

@tool
def list_sql_tables()->str:
    """
    查询当前库中所有可用的表！
    作用：为了模型识别有哪些可用的表！方便进行后续的自定义sql查询
    :return: 有表： 可用的表有：表1,表2,表3....  没有表: 没有可用的表   出现异常：查询出现异常：异常信息
    """

    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="数据库表名查询工具：list_sql_tables", args={})
    # 加载数据库信息配置
    config = get_db_config()

    # 1. 创建一个链接
    # 2. 创建cursor
    # 3. cursor执行sql语句
    # 4. cursor获取返回结果
    # 5. 释放连接和cursor资源
    # 确保要捕捉异常信息，返回异常提示，避免直接报错！
    try:
        # 确保资源使用完毕一定释放 with
        with connect(**config) as  conn:
            with conn.cursor() as cursor:
                sql = "show tables"
                cursor.execute(sql)
                # 捕捉执行结果 要所有的表名称
                # [(表1),(表2),(表3)]
                tables = cursor.fetchall()
                if not tables:
                    return "没有可用的表"
                # 可用的表有：表1,表2,表3....
                # [表1,表2,表3]
                table_names = [table[0] for table in tables]
                return f"可用的表有：{', '.join(table_names)}"
    except Error as e:
        return f"查询出现异常：{str(e)}"


@tool
def get_table_data(table_name)->str:
    """
    查询指定表名的数据！当前工具调用之前，必须先调用list_sql_tables完成表名的校验！
    此工具的作用：1.可以完成单表数据的查询 2. 可以为多表查询提供表结果信息（列名&数据格式）
    :param table_name: 表名
    :return: csv格式的数据（模拟表格数据格式）
             1.第一行是列信息，列之间使用,（英文的逗号）分割
             2.第二行开始是表数据，值之间也使用,(英文的逗号)分割
             3.行和行之间使用\n分割
             4.至多表数据查询100条
             例如：
                id,name,age\n -> 列头
                1,张三,18\n
                1,张三,18\n    -> 至多查询100条
                1,张三,18\n
                1,张三,18\n
    """
    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="数据库表数据查询工具：get_table_data", args={"table_name":table_name})

    # 表名安全校验：只允许合法标识符，防止拼接出注入 SQL
    if not _is_safe_identifier(table_name):
        return (f"拒绝执行：表名 '{table_name}' 含非法字符。"
                "反思提示：请先调用 list_sql_tables 确认真实表名后，仅用表名本身重新调用。")

    # 获取数据库参数
    config = get_db_config()
    # 1. 创建一个链接
    # 2. 创建cursor
    # 3. cursor执行sql语句
    # 4. cursor获取返回结果
    # 5. 释放连接和cursor资源
    # 确保要捕捉异常信息，返回异常提示，避免直接报错！
    try:
        # 1. 创建一个链接
        with connect(**config) as  conn:
            # 2. 创建cursor
            with conn.cursor() as cursor:
                # 3. cursor执行sql语句
                sql = f"select * from {table_name} limit 100"
                cursor.execute(sql)
                # 4. cursor获取返回结果
                # 4.1 获取列的信息
                # 返回的查询结果的列的信息
                # description => [(id,列长度...),(),()]
                # 如果查询没有结果 -》 description 也是None
                description = cursor.description
                if not description:
                    return f"数据表：{table_name}为空没有数据！"
                # 4.2 获取查询结果
                # description =>  [(id,列长度...),(date,....),()] => 元组 index = 0 列名
                # [列1,列2,列3...]
                columns = [ desc[0] for desc in description ] # [1,2,3,4]
                # 表数据
                # [(1,张三),(2,李四),(3,二狗子)]
                rows = cursor.fetchall()
                # (1,张三) -> ('1','张三') -> '1,张三'
                # ['1,张三','1,张三','1,张三','1,张三','1,张三']
                results = [ ",".join(map(str,row)) for row in rows]

                # columns -> csv -> header
                # id,name,age
                header_str = ",".join(columns)
                # '1,张三'\n
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        return f"查询出现异常：{str(e)}"


@tool
def execute_sql_query(query)->str:
    """
    执行自定义查询sql语句！切记：执行之前，需要通过执行 list_sql_tables明确表名！执行get_table_data
    明确表结构和数据格式！
    :param query: 要执行的自定义sql语句
    :return: csv格式的数据（模拟表格数据格式）
             1.第一行是列信息，列之间使用,（英文的逗号）分割
             2.第二行开始是表数据，值之间也使用,(英文的逗号)分割
             3.行和行之间使用\n分割
             4.至多表数据查询100条
             例如：
                id,name,age\n -> 列头
                1,张三,18\n
                1,张三,18\n    -> 至多查询100条
                1,张三,18\n
                1,张三,18\n
    """
    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="数据库表数据查询工具：execute_sql_query", args={"query":query})

    # 只读校验：连接为 autocommit，写/删/DDL 会立即生效，必须拒绝
    if not _is_readonly_sql(query):
        logger.warning("SQL 只读校验未通过，已拒绝执行: %s", query)
        return ("SQL 拒绝执行：本工具仅支持只读查询（SELECT / SHOW / DESC / EXPLAIN），"
                "不允许执行写入、修改、删除、建表等操作，也不允许多条语句或注释包裹。"
                "反思提示：请改写为单条只读查询语句后重新调用本工具。")

    # 获取数据库参数
    config = get_db_config()
    # 1. 创建一个链接
    # 2. 创建cursor
    # 3. cursor执行sql语句
    # 4. cursor获取返回结果
    # 5. 释放连接和cursor资源
    # 确保要捕捉异常信息，返回异常提示，避免直接报错！
    try:
        # 1. 创建一个链接
        with connect(**config) as  conn:
            # 2. 创建cursor
            with conn.cursor() as cursor:
                # 3. cursor执行sql语句
                cursor.execute(query)
                # 4. cursor获取返回结果
                # 4.1 获取列的信息
                # 返回的查询结果的列的信息
                # description => [(id,列长度...),(),()]
                # 如果查询没有结果 -》 description 也是None
                description = cursor.description
                if not description:
                    return f"执行自定义SQL语句查询没有结果，sql为：{query}！"
                # 4.2 获取查询结果
                # description =>  [(id,列长度...),(date,....),()] => 元组 index = 0 列名
                # [列1,列2,列3...]
                columns = [ desc[0] for desc in description ] # [1,2,3,4]
                # 表数据
                # [(1,张三),(2,李四),(3,二狗子)]
                rows = cursor.fetchall()
                # (1,张三) -> ('1','张三') -> '1,张三'
                # ['1,张三','1,张三','1,张三','1,张三','1,张三']
                results = [ ",".join(map(str,row)) for row in rows]

                # columns -> csv -> header
                # id,name,age
                header_str = ",".join(columns)
                # '1,张三'\n
                data_str = "\n".join(results)
                return f"{header_str}\n{data_str}"
    except Error as e:
        # 反思机制（self-healing SQL）：把错误信息和可用表清单回喂给模型，
        # 让模型自行修正 SQL 后重新调用，而不是拿到一句干巴巴的报错就放弃。
        logger.warning("SQL 执行失败，启用错误回喂: %s", e)
        feedback = (f"SQL 执行失败：{str(e)}\n"
                    "反思提示：请检查表名、字段名、语法是否正确，修正后重新调用本工具。\n")
        # 尽力附带当前库的表清单，帮助模型定位正确的表名
        try:
            with connect(**config) as conn2:
                with conn2.cursor() as cursor2:
                    cursor2.execute("show tables")
                    tables = [t[0] for t in cursor2.fetchall()]
                    if tables:
                        feedback += f"当前库中可用的表：{', '.join(tables)}。可先调用 get_table_data 预览表结构。"
        except Error:
            feedback += "（附加信息：当前无法查询表清单，请确认数据库连接配置）"
        return feedback



if __name__ == "__main__":
    print(execute_sql_query("SELECT * FROM `drugs` dgs join sales_records srd on dgs.drug_id = srd.drug_id"))






