"""
pytest 全局配置：在导入任何项目模块之前注入测试用环境变量，
保证 CI（无真实 API Key）环境下项目模块可以安全 import。
"""
import os
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中（pytest 从项目根目录运行）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------- 测试用假配置（只让客户端构造通过，不会发起真实网络请求） ----------
os.environ.setdefault("OPENAI_BASE_URL", "https://test.invalid/v1")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("LLM", "test-model")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test-key")
os.environ.setdefault("MYSQL_HOST", "localhost")
os.environ.setdefault("MYSQL_PORT", "3306")
os.environ.setdefault("MYSQL_USER", "test-user")
os.environ.setdefault("MYSQL_PASSWORD", "test-password")
os.environ.setdefault("MYSQL_DATABASE", "test-database")
os.environ.setdefault("RAGFLOW_API_URL", "http://test.invalid")
os.environ.setdefault("RAGFLOW_API_KEY", "test-ragflow-key")
