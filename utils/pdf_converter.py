import logging
from pathlib import Path

try:
    import markdown
except ImportError:
    markdown = None

logger = logging.getLogger(__name__)

# Markdown -> HTML 的统一样式（两套引擎共用；字体栈覆盖 Windows 中文字体与 Linux 容器内的 Noto CJK）
_MD_CSS = """
    body {
        font-family: "Noto Sans CJK SC", "Source Han Sans SC", "Microsoft YaHei", "SimHei", sans-serif;
        line-height: 1.6;
        padding: 24px;
    }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; }
    th, td { border: 1px solid #999; padding: 8px; }
    th { background-color: #f0f0f0; }
    pre { background-color: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
    code { font-family: "Consolas", "Monaco", monospace; }
    h1, h2, h3 { margin-top: 1.2em; }
"""


def _render_html(md_abs_path: Path) -> str:
    """Markdown 文件 -> 带样式的完整 HTML（供各 PDF 引擎共用）"""
    if markdown is None:
        raise RuntimeError("缺少依赖库，请安装: pip install markdown")
    md_content = md_abs_path.read_text(encoding='utf-8')
    html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>@page {{ size: A4; margin: 18mm 15mm; }} {_MD_CSS}</style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """


def convert_md_to_pdf_via_weasyprint(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    使用 WeasyPrint 将 Markdown 转换为 PDF。
    纯 Python 实现，跨平台（Windows / Linux / Docker 容器）均可运行。
    注意：Linux 容器内需安装中文字体（如 fonts-noto-cjk），否则中文会显示为方块。
    依赖：weasyprint, markdown
    """
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as e:
        # WeasyPrint 依赖系统级库（Pango 等），缺失时同样走降级
        logger.warning("WeasyPrint 不可用: %s", e)
        raise ImportError("WeasyPrint 未安装或缺少系统依赖") from e

    html_content = _render_html(md_abs_path)
    HTML(string=html_content, base_url=str(md_abs_path.parent)).write_pdf(str(pdf_abs_path))

    if pdf_abs_path.exists():
        return f"成功转换: {pdf_abs_path} (WeasyPrint引擎)"
    return f"转换完成但未生成文件: {pdf_abs_path}"


def convert_md_to_pdf_file(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    Markdown -> PDF 的统一入口（策略模式）：
      1. 优先使用 WeasyPrint：纯 Python、跨平台、可容器化；
      2. WeasyPrint 不可用时，若在 Windows 上则降级到 Word COM 引擎；
      3. 两者都不可用则返回明确的错误提示。
    """
    try:
        return convert_md_to_pdf_via_weasyprint(md_abs_path, pdf_abs_path)
    except ImportError:
        pass

    import os
    if os.name == 'nt':
        # Windows 本地备选引擎：Word COM（依赖 pywin32）
        from utils.word_converter import convert_md_to_pdf_via_word
        logger.info("WeasyPrint 不可用，降级使用 Word COM 引擎转换 PDF")
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)

    return ("转换失败: 未找到可用的 PDF 引擎。"
            "请安装 WeasyPrint（pip install weasyprint，Linux 需系统级 pango 库与中文字体），"
            "或在 Windows 上安装 pywin32 + Microsoft Word。")
