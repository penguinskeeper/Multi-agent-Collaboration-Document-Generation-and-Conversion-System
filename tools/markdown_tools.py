import logging
from pathlib import Path

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from langchain_core.tools import tool
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path, is_within

logger = logging.getLogger(__name__)


# Markdown生成工具
@tool
def generate_markdown(
        content: Annotated[str, "要写入Markdown文档的文本内容"],
        filename: Annotated[str, "Markdown文档的文件名（不包含扩展名或包含.md）"],
        path: Annotated[str, "文件保存的绝对路径"] = ""
):
    """根据提供的文本内容，生成对应的Markdown(.md)文件"""
    monitor.report_tool("Markdown文档生成工具", {"写入的文本内容": content})
    if not filename.endswith('.md'):
        filename += '.md'

    # 获取上下文中的会话目录
    session_dir = get_session_context()
    logger.debug("generate_markdown 拿到的 path=%s, session_dir=%s", path, session_dir)

    # --- 路径清洗与重定向逻辑 ---
    # 结合 path 和 filename
    if path and path != ".":
        # 使用 Path 拼接，再转为字符串传给 resolve_path
        full_input_path = str(Path(path) / filename)
    else:
        full_input_path = filename
    full_path_str = resolve_path(full_input_path, session_dir)
    file_path = Path(full_path_str)

    # 写入越权防护：resolve_path 对会话外绝对路径是"原样返回"的，
    # 必须在这里兜底，禁止把文件写到会话工作目录之外。
    if not session_dir:
        return "错误：当前没有会话工作目录上下文，无法确定保存位置。请通过任务接口正常发起请求。"
    if not is_within(str(file_path), session_dir):
        logger.warning("generate_markdown 拒绝越权写入: %s (会话目录: %s)", file_path, session_dir)
        return (f"拒绝写入：目标路径 '{file_path}' 不在会话工作目录内。"
                f"反思提示：请把 filename 改为相对文件名（如 '报告.md'），"
                f"文件会自动保存到工作目录 {session_dir} 下。")

    # 获取父目录
    parent_dir = file_path.parent

    # 确保目录存在
    logger.debug("[MarkdownTool] parent_dir=%s, filename=%s, full_path=%s",
                 parent_dir, filename, file_path)

    try:
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("[MarkdownTool] Created directory: %s", parent_dir)

        # 使用 Path 直接写入文本
        file_path.write_text(content, encoding='utf-8')

        logger.info("[MarkdownTool] Successfully wrote to: %s", file_path)
        return f"Markdown文件 '{file_path}' 已成功生成并保存。"
    except Exception as e:
        logger.error("[MarkdownTool] Error writing file: %s", e)
        return f"生成Markdown文件失败: {str(e)}"


# -------------------------- 测试代码（仅修改这里，给session_dir配置固定值） --------------------------
if __name__ == "__main__":
    # ========== 核心：覆盖get_session_context的返回值（仅测试时生效） ==========
    # 不用Mock，直接重新定义这个函数，给session_dir赋值！
    def get_session_context():
        """测试专用：给session_dir配置固定初始化值"""
        return "./test_session_123"  # 你要的session_dir初始化值，随便改

    # ========== 极简测试逻辑（只传path/filename，session_dir已初始化） ==========
    test_content = "# 测试文档\n这是给session_dir配置固定值后的测试内容"
    test_filename = "测试文件"  # 无.md后缀，测试自动补全
    test_path = "sub_dir"       # 相对路径

    # 调用生成函数
    print("===== 开始测试（session_dir已配置为：./test_session_123） =====")
    result = generate_markdown.invoke({
        "content": test_content,
        "filename": test_filename,
        "path": test_path
    })

    # 验证结果
    print(f"\n调用结果：{result}")
    if "已成功生成" in result:
        file_path = Path(result.split("'")[1])
        print(f"✅ 验证：文件 {file_path} {'存在' if file_path.exists() else '不存在'}")