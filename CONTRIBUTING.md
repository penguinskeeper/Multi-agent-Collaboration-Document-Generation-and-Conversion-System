# 贡献指南（Contributing）

感谢你有兴趣改进这个项目。它是一个**技术演示性质**的多智能体系统，
目标是"用尽量少的代码把一件完整的事做对"，所以对代码量增长比较克制——
相比新增功能，更欢迎**把已有部分写得更清楚**的改动。

## 环境准备

```bash
git clone https://github.com/penguinskeeper/deep-search-pro.git
cd deep-search-pro

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env      # 然后填入你自己的 LLM / Tavily 密钥
```

没有密钥也能跑测试：`tests/conftest.py` 会注入假的测试环境变量，外部依赖（LLM / Tavily /
RAGFlow / MySQL）都已 mock，CI 在无密钥环境下运行。

## 提交前自检

```bash
ruff check --select E9,F .   # 语法错误与未定义名称（与 CI 一致）
pytest -q                    # 42 个用例应全绿
```

## 提交规范

- **一个 PR 只做一件事**。重构与功能改动请分开，评审会快很多。
- **commit message 用祈使句描述"做了什么"**，例如 `fix: 修正静态资源的缓存头`。
- **新增行为要带测试**。这个项目最值得保留的习惯是"测试抓出过真 bug"——
  曾经的初始化时序问题、RAGFlow 导入即崩、reload 父进程漏杀，都是测试或实测发现的。
- **新增配置项必须进 `.env.example`**，并在 README 对应位置说明。
- **不要提交真实凭据**。数据库密码、API Key 一律走环境变量。

## 代码风格

| 项 | 约定 |
|---|---|
| 行宽 | 100 字符以内 |
| 类型 | 公开函数写类型标注 |
| 注释 | 解释**为什么**，不复述代码在做什么 |
| 中文 | 注释与文档用中文，变量/函数名用英文 |
| 路径 | 一律用 `pathlib`，不要在代码里出现本机绝对路径 |

## 特别欢迎的改动

`README.md` 的「路线图」一节列了明确可认领的方向，其中标注"低难度"的几项
（`rawflow/` 合并、依赖结构梳理）适合作为第一次贡献。

## 行为准则

保持专业与友善：就事论事地讨论技术，不对人。项目维护者有拒绝任何 PR 的权利，
但会说明理由。
