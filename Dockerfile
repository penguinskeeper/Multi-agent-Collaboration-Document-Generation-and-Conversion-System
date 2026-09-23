# ============================================================
# Deep Search Pro - 应用镜像
# 说明：
#   1. PDF 转换走 WeasyPrint（纯 Python），需系统级 Pango 库；
#      容器内安装 fonts-noto-cjk 保证中文 PDF 不出现方块。
#   2. 依赖 pywin32 的 Word COM 引擎仅在 Windows 本地作为兜底，
#      容器内不可用也无需安装（pdf_converter 会自动降级跳过）。
# ============================================================

FROM python:3.10-slim

# 系统依赖：
#   libpango / libharfbuzz / libffi  -> WeasyPrint 运行时
#   fonts-noto-cjk                   -> 中文字体（PDF 渲染必需）
#   default-libmysqlclient-dev 等    -> 预留（当前 mysql-connector-python 为纯 Python，无需编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libffi-dev \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单单独安装，充分利用 Docker 层缓存（代码改动不触发重装依赖）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目代码
COPY . .

# 运行时目录预创建（output 生成文件 / data 会话历史库）
RUN mkdir -p output updated data

EXPOSE 8000

# 生产运行：不带 --reload；如需热重载请在开发环境本地跑 python api/server.py
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
