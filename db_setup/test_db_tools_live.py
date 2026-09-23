"""数据库工具连通性验证脚本（从项目外部目录执行，同时验证 CWD 无关性）

用法：
    python db_setup/test_db_tools_live.py

路径不写死：以本文件位置推导项目根目录，任何机器上 clone 下来都能跑。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.db_tools import list_sql_tables, get_table_data, execute_sql_query  # noqa: E402

print("=== 1. list_sql_tables ===")
print(list_sql_tables.invoke({}))

print("=== 2. get_table_data(drugs) 前 3 行 ===")
out = get_table_data.invoke({"table_name": "drugs"})
print("\n".join(out.split("\n")[:3]))

print("=== 3. execute_sql_query 联表聚合 ===")
query = (
    "SELECT d.drug_name, SUM(s.total_amount) AS amt "
    "FROM drugs d JOIN sales_records s ON d.drug_id = s.drug_id "
    "GROUP BY d.drug_name ORDER BY amt DESC LIMIT 3"
)
print(execute_sql_query.invoke({"query": query}))

print("=== 4. 写操作拦截 ===")
print(execute_sql_query.invoke({"query": "DROP TABLE drugs"}))

print("=== 5. 非法表名拦截 ===")
print(get_table_data.invoke({"table_name": "drugs; DROP TABLE sales_records"}))

print("ALL_TOOL_TESTS_DONE")
