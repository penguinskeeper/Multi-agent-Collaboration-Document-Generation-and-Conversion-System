"""
utils/path_utils.py 的参数化测试：覆盖文档中列出的 12 种路径边界场景。
纯函数测试，不依赖外部服务。
"""
import sys
from pathlib import Path

import pytest

from utils.path_utils import resolve_path

WIN_SESSION_DIR = "D:/Project/output/session_123"


@pytest.mark.skipif(sys.platform != "win32", reason="期望值以 Windows 路径为准")
@pytest.mark.parametrize(
    "filename, session_dir, expected",
    [
        # 1. 虚拟路径清洗：剥离 /workspace 前缀 -> 拼接到会话目录
        ("/workspace/report.md", WIN_SESSION_DIR, "D:/Project/output/session_123/report.md"),
        # 2. updated/ 特殊处理：提取 updated/ 后路径，相对于 CWD 解析
        ("abc/updated/upload/file.pdf", WIN_SESSION_DIR, str(Path("updated/upload/file.pdf").resolve())),
        # 3. 无会话目录：直接解析为 CWD 下绝对路径
        ("sub/test.md", None, str(Path("sub/test.md").resolve())),
        # 4. 绝对路径（会话内）：直接返回
        ("D:/Project/output/session_123/sub/report.md", WIN_SESSION_DIR,
         "D:/Project/output/session_123/sub/report.md"),
        # 6. Windows Unix 风格绝对路径（/ 开头无盘符）：拼接到会话目录
        ("/sub/test.md", WIN_SESSION_DIR, "D:/Project/output/session_123/sub/test.md"),
        # 7. 路径嵌套防护：连续重复 session 名 -> 修正
        ("D:/Project/output/session_123/session_123/report.md", WIN_SESSION_DIR,
         "D:/Project/output/session_123/report.md"),
        # 8. 相对路径含 session 名：防止嵌套
        ("session_123/report.md", WIN_SESSION_DIR, "D:/Project/output/session_123/report.md"),
        # 9. 相对路径含 output 前缀：拼接到会话目录
        ("output/report.md", WIN_SESSION_DIR, "D:/Project/output/session_123/report.md"),
        # 10. 普通相对路径：拼接到会话目录
        ("sub1/sub2/test.md", WIN_SESSION_DIR, "D:/Project/output/session_123/sub1/sub2/test.md"),
        # 11. 虚拟路径 + updated：先剥离前缀，再触发 updated 处理
        ("/mnt/data/updated/doc.md", WIN_SESSION_DIR, str(Path("updated/doc.md").resolve())),
    ],
)
def test_resolve_path_windows_scenarios(filename, session_dir, expected):
    # 用 Path 相等性比较：Windows 下 resolve() 会规范化分隔符并折叠大小写
    assert Path(resolve_path(filename, session_dir)) == Path(expected)


@pytest.mark.skipif(sys.platform != "win32", reason="场景 5 的期望值依赖当前盘符解析")
def test_resolve_path_absolute_outside_session():
    # 5. 绝对路径（会话外）：保留原路径
    assert Path(resolve_path("D:/OtherDir/file.md", WIN_SESSION_DIR)) == Path("D:/OtherDir/file.md")


def test_resolve_path_no_session_returns_absolute():
    # 基本可用性：无 session_dir 时必须返回绝对路径
    result = resolve_path("some/file.md", None)
    assert Path(result).is_absolute()
