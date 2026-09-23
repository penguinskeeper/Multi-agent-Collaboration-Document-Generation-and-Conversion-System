# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中

- JWT 登录与多用户支持（当前为单机 demo 的静态 `X-API-Key`）
- API 限流（slowapi），避免 Agent 被刷产生 LLM 费用
- 合并 `rawflow/` 与主链路 `tools/ragflow_tools.py` 的重复实现
- 整理 `requirements.txt` 为「直接依赖 + 锁定版本」

---

## [1.0.0] - 2026-09

首个公开版本。

### 核心能力

- **多智能体编排**：主智能体调度网络搜索 / NL2SQL 数据库查询 / RAG 知识库三类子智能体，
  自动分解任务并汇总为 Markdown / PDF 报告
- **反思与自我修正**：搜索空结果三级降级重试、SQL 报错回喂错误与表清单（self-healing SQL）、
  RAG 短答案换角度引导
- **会话持久化**：`AsyncSqliteSaver` 落盘，服务重启后同一 `thread_id` 可续聊
- **实时进度推送**：WebSocket 推送工具调用链路，前端时间线实时可见
- **并发隔离**：`ContextVar` 协程级会话隔离
- **优雅降级**：MySQL / RAGFlow / checkpointer / PDF 引擎任一缺失均不阻断启动
- **安全加固**：路径穿越防护（12 类场景）、上传下载越权校验、CORS 白名单、
  `X-API-Key` 鉴权、上传类型与大小限制、数据库只读账号双保险
- **跨平台 PDF**：WeasyPrint 优先，Windows 上自动降级 Word COM
- **工程化**：pytest 42 个用例、GitHub Actions（3.10/3.11 矩阵 + 镜像构建）、
  Docker Compose 一键编排 app + MySQL

### 修复

- RAGFlow 客户端在模块顶层构造，未配置环境变量时 `import` 即崩溃 → 改为懒加载 + 降级
- `AsyncSqliteSaver` 的构造需要运行中的事件循环，模块级初始化会报错 → Agent 改为惰性单例
- `mysql-connector-python` 9.x 的 C 扩展在部分 Python 3.13 环境下段错误 → 强制 `use_pure=True`
- CORS 的 `allow_origins=["*"]` 与 `allow_credentials=True` 组合违反规范 → 改为白名单
- 静态资源缺少 `Cache-Control`，浏览器启发式缓存导致停服后仍显示旧页面 → 注入 `no-store`
- `uvicorn --reload` 的 reloader 父进程未被清理，只杀 worker 会导致端口复活

---

[Unreleased]: https://github.com/penguinskeeper/deep-search-pro/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/penguinskeeper/deep-search-pro/releases/tag/v1.0.0
