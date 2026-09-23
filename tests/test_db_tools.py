"""
tools/db_tools.py 测试：mock 掉 mysql.connector.connect，
验证工具的输出格式与异常处理，不依赖真实数据库。
"""
from unittest.mock import MagicMock, patch

import pytest

import tools.db_tools as db_tools


def _fake_cursor(columns, rows):
    cursor = MagicMock()
    cursor.description = [(c, None, None, None, None, None, None) for c in columns]
    cursor.fetchall.return_value = rows
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


def _fake_conn(cursor):
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


def test_list_sql_tables_formats_names():
    cursor = _fake_cursor([], [("drugs",), ("sales_records",)])
    with patch.object(db_tools, "connect", return_value=_fake_conn(cursor)):
        result = db_tools.list_sql_tables.invoke({})
    assert result == "可用的表有：drugs, sales_records"


def test_list_sql_tables_empty():
    cursor = _fake_cursor([], [])
    with patch.object(db_tools, "connect", return_value=_fake_conn(cursor)):
        result = db_tools.list_sql_tables.invoke({})
    assert result == "没有可用的表"


def test_get_table_data_returns_csv():
    cursor = _fake_cursor(
        ["drug_id", "drug_name"],
        [(1, "阿莫西林胶囊"), (2, "布洛芬缓释胶囊")],
    )
    with patch.object(db_tools, "connect", return_value=_fake_conn(cursor)):
        result = db_tools.get_table_data.invoke({"table_name": "drugs"})
    lines = result.split("\n")
    assert lines[0] == "drug_id,drug_name"
    assert lines[1] == "1,阿莫西林胶囊"
    assert lines[2] == "2,布洛芬缓释胶囊"


def test_get_table_data_empty_table():
    cursor = _fake_cursor([], [])
    cursor.description = None  # 空表时 description 为 None
    with patch.object(db_tools, "connect", return_value=_fake_conn(cursor)):
        result = db_tools.get_table_data.invoke({"table_name": "drugs"})
    assert "为空" in result


def test_execute_sql_query_formats_result():
    cursor = _fake_cursor(
        ["drug_name", "total"],
        [("阿莫西林胶囊", "110.60")],
    )
    with patch.object(db_tools, "connect", return_value=_fake_conn(cursor)):
        result = db_tools.execute_sql_query.invoke({"query": "SELECT 1"})
    assert result == "drug_name,total\n阿莫西林胶囊,110.60"


def test_missing_db_config_raises_value_error(monkeypatch):
    for key in ("MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError):
        db_tools.get_db_config()


def test_execute_sql_query_rejects_write_sql():
    # 只读防护：写/删/DDL 语句必须在连接前被拒绝（连接为 autocommit，写操作会立即生效）
    with patch.object(db_tools, "connect") as mock_connect:
        result = db_tools.execute_sql_query.invoke({"query": "DROP TABLE drugs"})
    mock_connect.assert_not_called()
    assert "拒绝执行" in result


def test_execute_sql_query_rejects_comment_wrapped_write():
    # 注释伪装绕过前缀校验也必须被拒绝
    with patch.object(db_tools, "connect") as mock_connect:
        result = db_tools.execute_sql_query.invoke({"query": "SELECT 1; DROP TABLE drugs"})
    mock_connect.assert_not_called()
    assert "拒绝执行" in result


def test_get_table_data_rejects_invalid_table_name():
    # 表名注入防护：含非法字符的表名必须在连接前被拒绝
    with patch.object(db_tools, "connect") as mock_connect:
        result = db_tools.get_table_data.invoke({"table_name": "drugs; DROP TABLE drugs"})
    mock_connect.assert_not_called()
    assert "拒绝执行" in result
