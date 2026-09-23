import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple, Optional

# 项目根目录（rawflow -> parents[1] = 项目根），避免依赖 CWD 解析 .env
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _load_ragflow_env() -> Tuple[Optional[str], Optional[str]]:
    """
    加载 RAGFlow 环境变量（优先读取项目根目录 .env，兼容系统环境变量）
    返回值：(api_key, base_url) → 缺失则返回 None
    """
    # 优先加载项目根目录的 .env 文件（不依赖当前工作目录）
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # 无则加载系统环境变量

    api_key = os.getenv("RAGFLOW_API_KEY")
    base_url = os.getenv("RAGFLOW_API_URL")
    return api_key, base_url