"""
3.2 反思/重试机制测试：
  - tavily: 空结果自动重试（简化关键词/回退 topic），全失败返回 reflection 引导
  - db_tools: SQL 报错回喂错误信息 + 可用表清单（self-healing）
  - ragflow: 答案过短返回换角度提示
依赖 tavily-python / ragflow-sdk 的用例用 importorskip 保护，
本地没装也能跳过，CI 全量环境会真实执行。
"""
from unittest.mock import MagicMock, patch

import pytest

import tools.db_tools as db_tools


# ============================ db_tools: self-healing SQL ============================

def _make_conn_with_sql_error_then_tables(tables):
    """
    构造一个 mock 连接：
      第一次 execute（业务 SQL）抛 Error；
      第二次 execute（show tables）返回表清单。
    """
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    from mysql.connector import Error
    cursor.execute.side_effect = [Error("Unknown column 'foo' in 'where clause'"), None]
    cursor.fetchall.side_effect = [[(t,) for t in tables]]

    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    conn.cursor.return_value = cursor
    return conn


def test_execute_sql_error_returns_self_healing_feedback():
    conn = _make_conn_with_sql_error_then_tables(["drugs", "sales_records"])
    with patch.object(db_tools, "connect", return_value=conn):
        result = db_tools.execute_sql_query.invoke({"query": "SELECT foo FROM bar"})

    assert "SQL 执行失败" in result
    assert "反思提示" in result
    assert "drugs, sales_records" in result  # 表清单已回喂给模型


def test_execute_sql_error_without_table_list_still_guides(monkeypatch):
    # 第二次查询表清单也失败时，仍要给出反思引导
    from mysql.connector import Error

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    cursor.execute.side_effect = [Error("Table 'x' doesn't exist"), Error("conn lost")]

    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    conn.cursor.return_value = cursor

    with patch.object(db_tools, "connect", return_value=conn):
        result = db_tools.execute_sql_query.invoke({"query": "SELECT 1"})

    assert "SQL 执行失败" in result
    assert "反思提示" in result


# ============================ tavily: 空结果重试 ============================

def test_tavily_retries_then_succeeds():
    pytest.importorskip("tavily")
    import tools.tavily_tool as tt

    responses = [
        {"results": []},                      # 第1次：空 -> 简化关键词
        {"results": []},                      # 第2次：空 -> topic 回退/再简化
        {"results": [{"title": "hit", "url": "https://x.com"}]},  # 第3次：命中
    ]
    mock_client = MagicMock()
    mock_client.search.side_effect = responses

    with patch.object(tt, "tavily_client", mock_client):
        result = tt.internet_search.invoke({"query": "最近的 AI Agent 进展如何？？"})

    assert mock_client.search.call_count == 3
    assert result["results"][0]["title"] == "hit"


def test_tavily_all_fail_returns_reflection():
    pytest.importorskip("tavily")
    import tools.tavily_tool as tt

    mock_client = MagicMock()
    mock_client.search.return_value = {"results": []}

    with patch.object(tt, "tavily_client", mock_client):
        result = tt.internet_search.invoke({"query": "一个非常冷门的问题"})

    assert result["results"] == []
    assert "reflection" in result
    assert "反思" in result["reflection"]
    assert mock_client.search.call_count == tt._MAX_SEARCH_ATTEMPTS


def test_simplify_query_strips_punctuation():
    pytest.importorskip("tavily")
    import tools.tavily_tool as tt
    assert tt._simplify_query("最近的，AI Agent 进展？") == "最近的 AI Agent 进展"


# ============================ ragflow: 答案过短反思 ============================

def test_ragflow_short_answer_returns_reflection():
    pytest.importorskip("ragflow_sdk")
    import tools.ragflow_tools as rf

    chat = MagicMock()
    session = MagicMock()
    session.ask.return_value = [MagicMock(content="不知道")]  # 过短
    chat.create_session.return_value = session
    session.id = "sess-1"
    chat.datasets = []
    mock_client = MagicMock()
    mock_client.list_chats.return_value = [chat]

    with patch.object(rf, "_get_ragflow_client", return_value=mock_client):
        result = rf.create_ask_delete.invoke({"chat_name": "药品知识助手", "question": "1+1=?"})

    assert "反思提示" in result
    chat.delete_sessions.assert_called_once()  # 会话仍被正常关闭


def test_ragflow_normal_answer_passthrough():
    pytest.importorskip("ragflow_sdk")
    import tools.ragflow_tools as rf

    answer = "感冒药通常建议在饭后服用，避免刺激肠胃，具体请遵医嘱。"
    chat = MagicMock()
    session = MagicMock()
    session.ask.return_value = [MagicMock(content=answer)]
    chat.create_session.return_value = session
    session.id = "sess-1"
    chat.datasets = []
    mock_client = MagicMock()
    mock_client.list_chats.return_value = [chat]

    with patch.object(rf, "_get_ragflow_client", return_value=mock_client):
        result = rf.create_ask_delete.invoke({"chat_name": "药品知识助手", "question": "感冒药怎么吃"})

    assert result == answer
