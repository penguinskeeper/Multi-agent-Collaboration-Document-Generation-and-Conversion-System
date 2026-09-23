# 设计说明（Design Notes）

本文记录这个项目里几个关键选择的**动机与权衡**，而不是罗列代码在做什么。
如果你只想跑起来，看 [README](../README.md) 就够了；想理解"为什么这么写"，再往下读。

---

## 1. 编排层：为什么用 deepagents 而不是自己写调度

一个多智能体系统的核心难点不在"调用几个工具"，而在这四件事：

- 状态在多个子智能体之间怎么流转；
- 主智能体如何根据 `description` 决定把任务交给谁（tool_call 路由）；
- 中间过程如何流式输出给前端；
- 某一环失败了怎么恢复。

自研编排意味着这四件都要自己实现一遍。`deepagents` 把编排骨架封装掉了——你只需要
给每个子智能体定义 `name` / `description` / `tools` 三件东西，框架负责调度。

**代价**：可控性下降，遇到框架层面的怪异行为需要读源码。
**判断**：这是学习项目，先用框架跑通"多智能体能做什么"，再去读源码理解"框架怎么做到的"，
比一上来手搓调度器更有效率。

---

## 2. 会话持久化：从 InMemorySaver 到 AsyncSqliteSaver

最初的实现用 `InMemorySaver`，服务一重启会话历史就没了。换成 SQLite 落盘后，
同一个 `thread_id` 跨重启可以继续对话。

但换过来时踩到一个真实的时序问题，值得记录下来：

**SQLite checkpointer 的构造需要一个"正在运行的事件循环"。** 如果按常规做法在模块导入时
就把它建好（模块级全局对象），在 FastAPI 启动阶段会报错。

**解法是把 Agent 构建改成惰性单例**：第一次真正收到请求（此时事件循环必然已在运行）才
初始化 Agent 与 checkpointer，并用锁保证并发下只构建一次。

这类"同步初始化遇上异步运行时"的时序冲突，是异步项目里最容易反复踩的一类坑。

**降级路径**：若环境里没装 `langgraph-checkpoint-sqlite`，代码会退回内存保存并打印 warning，
不阻断启动。功能受限但服务可用——比直接崩掉好。

---

## 3. 反思 / 自我修正（Reflection）

三个子智能体各自带一套失败处理，这是整个项目里最能体现"Agentic"味的部分：

| 子智能体 | 失败形态 | 处理策略 |
|---|---|---|
| 网络搜索 | 结果为空 / 相关性低 | 三级降级重试：换关键词 → 换检索角度 → 回喂 reflection 提示让模型自己重想 |
| 数据库 | SQL 执行报错 | 把**错误原文 + 当前可用表清单**一起回喂模型，让它自己改 SQL 重试（self-healing SQL） |
| 知识库 | 检索到的答案过短 | 引导模型换一个提问角度重新检索，而非直接返回空 |

设计上有一条共同原则：**不要把错误吞掉，要把它变成模型的输入。**
模型看不到错误就只能瞎猜，看到了错误才可能修正。

---

## 4. 并发隔离：为什么是 ContextVar

FastAPI 下多个请求跑在同一个线程的不同协程里。用全局变量存"当前会话目录 / thread_id"，
用户 A 的请求会被用户 B 覆盖——就是典型的串台。

`threading.local()` 在这里不管用，因为它按**线程**隔离，而这些协程共享同一个线程。
`ContextVar` 是 Python 为 asyncio 设计的**协程级**变量，每个请求链路各自独立，
才是对的工具。具体实现见 [`api/context.py`](../api/context.py)。

---

## 5. 实时进度推送：同步线程与事件循环之间怎么投递

工具函数是在**线程池**里执行的，而 WebSocket 推送必须回到**主事件循环**。
这两者之间怎么安全传递事件，取决于调用发起的位置：

- 已经在事件循环里 → `asyncio.create_task()`
- 在别的线程里 → `asyncio.run_coroutine_threadsafe()`

判断错就会抛 `no running event loop` 或静默丢事件。`api/monitor.py` 里的埋点统一做了
归属判断，工具函数只管调用同一个上报接口，不用关心自己在哪个线程。

---

## 6. 渐进式降级：可选依赖不阻断启动

MySQL、RAGFlow 都不是必需依赖。缺哪个，主智能体就跳过对应的子智能体，
只配 LLM + Tavily 也能跑通"搜索 → 汇总 → 生成报告"的完整链路。

这条原则贯穿整个项目：

| 缺失项 | 行为 |
|---|---|
| MySQL 未配 | 跳过数据库子智能体 |
| RAGFlow 未配 | 跳过知识库子智能体 |
| `API_KEY` 留空 | 进入开发模式，接口不鉴权 |
| SQLite checkpointer 缺失 | 降级为内存保存 + warning |
| WeasyPrint 缺系统库 | 自动切 Word COM 转 PDF |
| 前端静态页 | 带 `Cache-Control: no-store`，避免停服后浏览器仍渲染缓存旧页面 |

对使用者来说，项目"部分可用"比"直接起不来"有价值得多。

---

## 7. PDF 转换：把平台耦合剥离出来

初版直接用 Word COM（`pywin32`）转 PDF——**只有 Windows 能用，容器里必然失败**，
等于把 Docker 部署的路堵死了。

改成策略模式（[`utils/pdf_converter.py`](../utils/pdf_converter.py)）：

- **首选 WeasyPrint**：纯 Python，跨平台，容器可用；需装 Pango 与中文字体
- **兜底 Word COM**：Windows 本机若缺 Pango 系统库，自动降级，不打断用户

Docker 镜像里预装了 `fonts-noto-cjk` 与 Pango，中文不会渲染成方块。

---

## 8. 安全设计：三层

| 层 | 措施 |
|---|---|
| **文件层** | 路径穿越防护覆盖 12 类边界场景（`utils/path_utils.py`）；上传 / 下载接口均做越权校验 |
| **数据库层** | 应用层正则只读校验（`_is_readonly_sql()`）**+** 数据库层专用账号只授 `SELECT` ——双保险，正则被绕过也写不进去 |
| **接口层** | CORS 白名单（`API_ALLOWED_ORIGINS`）、`X-API-Key` 校验、上传扩展名白名单 + 20MB 大小限制 |

设计取向上有一个明确的判断：**安全校验不应该只有一道。** 应用层的校验会被 bug 绕过，
所以数据库层再设一道权限边界；反过来，只靠数据库权限又会给出难懂的报错，
所以应用层先拦一次给出人类可读的提示。

**未实现**：JWT 登录、API 限流（见第 9 节）。

---

## 9. 已知限制与后续规划

| 项 | 状态 |
|---|---|
| JWT 登录 | 未实现。当前用 `X-API-Key` 静态密钥，适合单机 demo，不适合多用户 |
| API 限流（slowapi） | 未实现。公开部署前建议加上——Agent 被刷会产生真实 LLM 费用 |
| RAGFlow 知识库 | 演示环境未接通（需付费云端或 16GB 内存自建），链路按设计降级；`ragflow_docs/` 素材待导入 |
| CI 中的 Docker 构建 | 本地开发机未装 Docker，该步骤由 GitHub Actions 验证 |
| 数据库脚本两套并存 | `data/seed_demo.sql`（Docker 主线，`pharma_demo`）与 `db_setup/`（本机手工部署，`pharma_mall`），详见 [db_setup/README.md](../db_setup/README.md) |

---

## 10. 开发过程中修掉的真实缺陷

1. **RAGFlow 客户端在模块顶层构造** → 没配环境变量时 `import` 即崩溃。
   改为懒加载 + 优雅降级。
2. **`AsyncSqliteSaver` 构造时序冲突** → 见第 2 节，改为惰性单例。
3. **`mysql-connector-python` 9.x 的 C 扩展在部分 Python 3.13 下直接段错误**
   （进程崩溃，`try/except` 捕不到）→ `get_db_config()` 强制 `use_pure=True`。
4. **CORS 配置违反规范**：`allow_origins=["*"]` 与 `allow_credentials=True` 不能共存
   → 改为环境变量驱动的白名单。
5. **静态资源缺少 `Cache-Control`** → Starlette 的 `StaticFiles` 只发 `Last-Modified`/`ETag`，
   浏览器会按启发式规则自行缓存（约 `(now - Last-Modified) × 10%`），
   导致停止服务后访问 `localhost:8000` 仍能看到旧页面，误以为服务还在跑。
   改为自定义 `NoCacheStaticFiles` 注入 `no-store`。
6. **停止脚本漏杀 reloader 父进程**：`uvicorn --reload` 是"父进程 + worker"结构，
   只杀占用端口的 worker，父进程会立刻把 worker 拉起来，端口复活。
   改为按命令行特征匹配清理，父子通杀。
