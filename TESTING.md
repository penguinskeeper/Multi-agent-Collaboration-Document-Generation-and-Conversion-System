# Deep Search Pro 测试手册

本文档给出六层测试的具体操作步骤，命令可直接复制执行。全程不需要修改任何代码。

> **路径约定**：本文档用 `<项目根目录>` 表示项目所在的文件夹、`<MYSQL_HOME>` 表示
> MySQL 的安装目录（本机可能是 `D:\MySQL`）。请按你自己的实际路径替换后再执行。

---

## 0. 测试环境现状

| 项 | 值 |
|---|---|
| 项目根目录 | `<项目根目录>` |
| Python 解释器（依赖已装齐） | 见下方「解释器怎么定」——项目内 `.venv`，或 `.dsp-python.txt` 里记录的本机解释器 |
| 测试框架 | pytest 8.3.4（`requirements-dev.txt`） |
| 静态检查 | ruff 0.9.6（只查 E9/F：语法错误、未定义名称，与 CI 一致） |
| 测试用例总数 | 42（`tests/` 下 4 个文件） |
| API 服务 | `http://localhost:8000`（演示页 `/`，接口文档 `/docs`） |
| MySQL | `127.0.0.1:3306`，库 `pharma_mall` |

### 解释器怎么定

机器上装了多个 Python（比如同时有 Anaconda）时，最容易踩的坑就是"命令跑起来了，但环境里没有依赖"，
典型报错是 `No module named uvicorn`。本项目统一用**逐个实测**的方式挑解释器，按下面的顺序取第一个
能 `import uvicorn` 成功的：

1. 环境变量 `DSP_PYTHON`
2. 项目内 `.venv\Scripts\python.exe`
3. 项目根目录下的 `.dsp-python.txt`（**一行**解释器路径，已被 gitignore；依赖装在项目外时用它）
4. PATH 上的 `python` / `py`

`start_api.bat` 用的就是这套规则；四个都不可用时它会直接报错，而不是带着错环境硬起。
**下文所有命令里的解释器路径，都请按同一结论替换**——本机若没有 `.venv`，就用 `.dsp-python.txt` 里记的那个。

### 命令前先设一次，省得每次敲长路径

打开 **CMD**，粘贴：

```cmd
cd /d "<项目根目录>"
set PY=<项目根目录>\.venv\Scripts\python.exe
:: 没有 .venv 时，换成 .dsp-python.txt 里记的解释器路径（见上文「解释器怎么定」）
```

**`set` 只对当前窗口有效，每开一个新窗口都要重设一次**。

---

## 0.5 在 VS Code 里跑（推荐，已配好）

`.vscode/` 下已有三份配置，**不需要手工敲命令**（这三份是个人配置、未入库：`.gitignore` 只放行
`.vscode/extensions.json`，所以从仓库克隆下来后需要自己建，或直接用上面的命令行方式）：

| 文件 | 作用 |
|---|---|
| `settings.json` | 解释器已指向装好依赖的环境；pytest 自动发现已开启 |
| `tasks.json` | 7 个一键任务（见下） |
| `launch.json` | 3 个调试配置（F5 用） |

### 前置：装扩展 + 选解释器

1. 扩展市场装 **Python**（`ms-python.python`）——测试面板和 `launch.json` 都依赖它
2. 打开 `<项目根目录>`（File → Open Folder）
3. `Ctrl+Shift+P` → 输入 `Python: Select Interpreter` → 选：
   ```
   <项目根目录>\.venv\Scripts\python.exe
   ```
   （`settings.json` 已配好默认值，正常会自动选中）

### 方式 A：测试面板（最省事，推荐）

1. 点左侧活动栏的**烧瓶图标**（Testing）——没有的话 `Ctrl+Shift+P` → `Testing: Focus on Test Explorer View`
2. 首次打开点一下 **Refresh Tests**（刷新按钮），它会扫描 `tests/` 目录
3. 树里会出现 4 个文件、42 个用例，每个用例左边有 ▶：
   - 点**单个用例的 ▶** → 只跑那一个
   - 点**文件级的 ▶** → 跑该文件
   - 点**顶部工具栏的 ▶** → 跑全部 42 个
4. 跑完：绿勾=通过，红叉=失败；**点失败项会在编辑器里高亮断言差异**，比看终端输出直观

> 想每次保存文件时自动重跑：`Ctrl+Shift+P` → `Testing: Toggle Test Auto Run`。

### 方式 B：任务面板（一键启动各类测试）

`Ctrl+Shift+P` → 输入 `Tasks: Run Task` → 选择：

| 任务名 | 干什么 | 消耗额度 |
|---|---|---|
| 测试：全部用例（pytest -v） | 42 个用例，逐个列名 | 否 |
| 测试：快速回归（pytest -q） | 只看摘要 | 否 |
| 测试：当前打开的文件 | 先在编辑器打开某个 `test_*.py` | 否 |
| 检查：ruff 静态检查（CI 同款） | 语法错 / 未定义名称 | 否 |
| 测试：数据库工具（连真实 MySQL） | 需 MySQL 在跑 | 否 |
| 测试：端到端（WebSocket 实时推送） | 真实 LLM 调用，1-3 分钟 | **是** |
| 服务：启动 API（info 日志） | 起服务，Ctrl+C 停 | 否 |

更快的入口：`Ctrl+Shift+P` → `Tasks: Run Test Task`（已把"全部用例"设为默认测试任务）。

### 方式 C：直接在 VS Code 终端里敲

`Ctrl + `` ` `` 打开终端。**先看终端类型**（终端面板右上角能切换，标题会显示 PowerShell / cmd / bash），语法各不相同：

**PowerShell（Windows 默认）** —— 路径带空格必须加 `&`：
```powershell
cd "<项目根目录>"
$py = "<项目根目录>\.venv\Scripts\python.exe"
& $py -m pytest -v
```

**CMD**：
```cmd
cd /d "<项目根目录>"
set PY=<项目根目录>\.venv\Scripts\python.exe
%PY% -m pytest -v
```

**Git Bash**：
```bash
cd "/g/agent study"
PY="./.venv/Scripts/python.exe"
"$PY" -m pytest -v
```

**先验证终端里的 `python` 指向对不对**（选错环境会导致莫名其妙的失败）：
```powershell
python -c "import sys; print(sys.executable)"
```
输出应是 `...binaries\python\envs\default\Scripts\python.exe`。若显示 `D:\anaconda\python.exe` 之类，说明环境没激活——用上面的绝对路径写法，或点终端里重新选解释器。

---

## 第 1 层：静态检查（秒级）

```cmd
%PY% -m ruff check --select E9,F --no-cache .
```

- **预期**：`All checks passed!`
- 只抓硬错误（语法错、用了未定义的名字），和 GitHub CI 跑的是同一条命令
- 想看更严格的风格问题（会有一堆历史遗留告警，属正常）：

```cmd
%PY% -m ruff check .
```

---

## 第 2 层：自动化测试（核心，约 10 秒）

```cmd
%PY% -m pytest
```

- **预期**：`42 passed`
- `pytest.ini` 已配好 `testpaths = tests`，在项目根直接跑就会自动找用例
- **这一层完全隔离**：`tests/conftest.py` 注入了假的 API Key 和假数据库配置，所有外部调用都被 mock 掉——不联网、不连数据库、**不消耗 DeepSeek / Tavily 额度**，可以随便反复跑

### 按文件或按用例单独跑

```cmd
:: 只跑接口层
%PY% -m pytest tests/test_api_server.py

:: 只跑数据库工具层
%PY% -m pytest tests/test_db_tools.py

:: 只跑反思机制（搜索降级 / SQL 报错回喂 / RAG 短答案）
%PY% -m pytest tests/test_reflection_tools.py

:: 只跑路径安全场景
%PY% -m pytest tests/test_path_utils.py

:: 按关键字挑用例（-k 后面是用例名的一部分）
%PY% -m pytest -k readonly
%PY% -m pytest -k apikey
```

### 要看清每个用例的名字和结果

```cmd
%PY% -m pytest -v
```

`-v` 会把 42 个用例逐个列出来（含参数化的路径场景），想知道"到底测了什么"就看这个。

### 想看 print 输出 / 卡住时定位

```cmd
%PY% -m pytest -v -s
```

`-s` 不吞 stdout；若某个用例挂住不返回，用 `Ctrl + C` 中断，它会打印当前卡在哪个用例。

---

## 第 3 层：数据库工具连真实 MySQL（秒级）

这一层会真的连库，**前提是 MySQL 在运行**。

**先确认 MySQL 活着**（没有输出代表没在跑，见第 7 节）：

```cmd
netstat -ano | findstr :3306
```

**跑工具验证脚本**（连通性 + 两道安全拦截）：

```cmd
%PY% -u db_setup\test_db_tools_live.py
```

**预期输出**：

```
=== 1. list_sql_tables ===
drugs
sales_records
=== 2. get_table_data(drugs) 前 3 行 ===
drug_id,drug_name,category,...
=== 3. execute_sql_query 联表聚合 ===
（销售额 Top3 药品）
=== 4. 写操作拦截 ===
（拒绝执行：仅允许只读查询...）
=== 5. 非法表名拦截 ===
（拒绝执行：表名不合法...）
=== ALL_TOOL_TESTS_DONE
```

第 4、5 步是**故意发起的攻击测试**，返回拒绝提示才是正确结果。脚本从项目外部路径也能跑（内部写死了 sys.path），顺带验证了配置加载不依赖当前工作目录。

---

## 第 4 层：HTTP 接口测试

服务没在跑就先起（见第 7 节）。下面用 **PowerShell**（JSON 引号不用转义，比 CMD 顺手）。

**① 健康检查**

```powershell
Invoke-WebRequest -Uri http://localhost:8000/ -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest -Uri http://localhost:8000/docs -UseBasicParsing | Select-Object StatusCode
```

预期都是 `200`。

**② 提交任务**

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/task -Method Post `
  -ContentType "application/json" -Body '{"query":"查询数据库中共有多少种药品"}'
```

**预期返回**：`{"status":"accepted","thread_id":"xxxx-xxxx-..."}`

拿到 `thread_id` 就说明受理成功。注意：**这个接口会真的启动智能体**，后面的执行会消耗 DeepSeek / Tavily 额度。只想验证接口的话，看返回里有 thread_id 就够了。

**③ 路径安全测试（验证越权拦截）**

```powershell
# 试图下载项目根目录的文件 → 应被拒绝
Invoke-WebRequest -Uri "http://localhost:8000/api/download?path=<项目根目录>\README.md" -UseBasicParsing
```

**预期**：`403`（拒绝访问，只能下载输出目录下的文件）。

```powershell
# 试图列举项目根目录 → 应被拒绝
Invoke-WebRequest -Uri "http://localhost:8000/api/files?path=<项目根目录>" -UseBasicParsing
```

**预期**：`403`。

**④ 上传测试**

```powershell
# 合法类型（md）→ 应成功
curl.exe -X POST http://localhost:8000/api/upload -F "files=@<项目根目录>\ragflow_docs\01_对乙酰氨基酚药品说明书.md"

# 非法类型（exe）→ 应返回 415
curl.exe -X POST http://localhost:8000/api/upload -F "files=@C:\Windows\System32\cmd.exe"
```

---

## 第 5 层：前端页面交互测试（功能验收，核心）

这一层就是"点着试"：真实启动智能体、真实调用模型。前面的层管代码有没有问题，这一层管**功能好不好使**。

### 5.1 前置：两个服务都在跑

| 服务 | 怎么确认 | 没有就启动 |
|---|---|---|
| MySQL | `netstat -ano \| findstr :3306` 有 LISTENING | 双击 `<MYSQL_HOME>\start_mysql.bat` |
| API 服务 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` 返回 `200` | 见第 7 层启动命令 |

### 5.2 打开页面，先确认这三处

浏览器打开 `http://localhost:8000/`，**别急着提问**，先看：

1. 左上标题 `🤖 Deep Search Pro`，副标题写着"主智能体 × 3 子智能体"
2. **右上角状态灯** —— 发第一个任务前显示灰点"未连接"，这是**正常的**（页面此时还没建 WebSocket）；发出任务后应变绿点 + "实时通道已连接"
3. 右栏两个空状态："暂无进度，先发一个任务吧" / "任务完成后在这里查看产出"

### 5.3 界面地图

| 区域 | 位置 | 作用 |
|---|---|---|
| 对话 | 左栏上半 | 对话记录；你的提问和智能体回复都落在这里 |
| 输入框 | 左栏底部 | 输入任务，**Ctrl + Enter** 或点「发送」；执行中「发送」按钮会临时禁用 |
| 执行进度（实时推送） | 右栏上半 | 智能体每一步动作的时间线，每条带时间戳 |
| 生成的文件 | 右栏下半 | 产出文件：文件名 + 大小 + 「下载」链接 |

**时间线图标速查**（判断智能体到底干了什么，全看这个）：

| 图标 | 事件类型 | 含义 |
|---|---|---|
| 🔧 | `tool_start` | 调用了工具（联网搜索 / SQL 查询 / 读写文件） |
| 🤝 | `assistant_call` | 调度子智能体、模型思考中 |
| ✅ | `task_result` | 任务完成，最终结果同时出现在左侧对话里 |
| ❌ | `error` | 出错（含内容风控拦截、工具执行失败） |
| ℹ️ | 其他 | 会话创建、状态提示 |

### 5.4 测试用例清单

按顺序做，每条都写了"看哪里、预期什么"：

| # | 场景 | 输入这句 | 观察点 | 预期 |
|---|---|---|---|---|
| 1 | **数据库查询** | 查询数据库中销售额最高的 5 种药品，给出名称、分类和销售额并分析 | 时间线出现 🔧数据库工具、🤝子智能体调度 | ✅ 完成，左侧给出真实药品名和金额 |
| 2 | **联网搜索** | 搜索 2026 年医药电商行业的主要趋势，总结三点 | 时间线出现 🔧搜索工具 | ✅ 带来源信息的总结 |
| 3 | **生成文件** | 把刚才的结论整理成一份 Markdown 报告，文件名 pharma_report.md | 右栏「生成的文件」是否出现条目 | 出现 `pharma_report.md` + 大小，点「下载」能拿到 |
| 4 | **转 PDF** | 把刚才的报告转成 PDF | 文件列表条目数 | 多一个 `.pdf` 文件 |
| 5 | **多轮追问** | 那第二名是哪个？ | 左侧对话 | 正确接上文（同一会话，智能体记得上下文） |
| 6 | **混合调度** | 对比一下数据库里的销售情况和网上的行业趋势 | 时间线是否出现**多个** 🤝 | 依次调度数据库 + 搜索两个子智能体 |
| 7 | **知识库（当前受限）** | 布洛芬和对乙酰氨基酚有什么区别？ | 时间线是否尝试调度知识库子智能体 | ⚠️ 会失败并降级——RAGFlow 云端 API 需付费档，属已知限制，**不是 bug** |
| 8 | **错误路径** | 先停掉 MySQL，再问"数据库中药品总数是多少" | ❌ 图标与文案 | 报错但服务不崩；重新启动 MySQL 后换个问法可恢复 |

### 5.5 对话框的两个行为（测试时必须知道）

1. **多轮追问共用同一会话**：页面用同一个 `thread_id` 连续提问，所以智能体记得上文。**要测独立场景必须先刷新页面开新会话**，否则会串上下文（比如上一个任务的结论会干扰这一次）
2. 每次点「发送」会**清空右栏时间线和文件列表**（左侧对话历史保留）—— 所以想看上一轮的文件列表，得趁下次发送前看

### 5.6 用 F12 精确验证推送（可选，但最硬核）

按 `F12` → **Network** 标签 → 筛选框输入 `ws`：

- 点开 `ws/<thread_id>` → **Messages** 标签 → 能看到每一条 JSON 报文，形如：
  ```json
  {"type":"monitor_event","event":"tool_start","message":"..."}
  ```
  这就是右侧时间线的原始数据源。任务卡住时看这里，能确定"报文到底有没有推出来"
- 切到 **Fetch/XHR** 筛选：能看到 `/api/task` 的响应（里面有 `thread_id`）、`/api/files` 的响应（文件清单）。**`thread_id` 就是本次会话目录名**

### 5.7 文件产物在哪

```
<项目根目录>\output\session_<thread_id>\
```

页面「下载」按钮拿的就是这个目录下的文件。想看某次任务的产物，用 5.6 里拿到的 `thread_id` 去 `output\` 下找同名文件夹。

### 5.8 三种"看着像故障其实正常"的情况

| 现象 | 真相 |
|---|---|
| 任务返回"内容审核未通过 / Content Exists Risk" | DeepSeek 服务端风控拦截，不是项目问题。换中性表述重问，或**刷新页面开新会话**（同一会话上下文里带着被拦内容会反复失败） |
| 问知识库问题失败 | RAGFlow 尚未接通（云端 API 需付费档 / 自建需 16GB 内存机器），项目按设计降级，其余子智能体不受影响 |
| 服务窗口里看不到执行日志 | 启动命令漏了 `--log-level info`。**真正的执行记录在页面右侧时间线**，那里才是准的 |

### 方式 B：WebSocket 脚本（黑框里看同样的推送流）

```cmd
%PY% -u db_setup\e2e_db_test.py
```

**预期**：打印 `THREAD:`、若干条 `[工具调用]` 事件，最后是 `TASK_RESULT:` 加上完整的自然语言分析。内容与前端的实时推送一致，适合不方便开浏览器时快速验一遍。

---

## 第 6 层：安全专项测试

### ① 鉴权测试（当前是开发模式放行，需手工开启才能测）

现在 `.env` 里 `API_KEY=` 是空的 → 服务处于**开发模式，所有接口直接放行**。要测鉴权，临时打开：

1. 编辑 `<项目根目录>\.env`，把 `API_KEY=` 改成 `API_KEY=test123`
2. **重启服务**（`.env` 只在启动时读一次）
3. 跑以下验证：

```powershell
# 不带密钥 → 预期 401
try { Invoke-WebRequest -Uri http://localhost:8000/api/task -Method Post -ContentType "application/json" -Body '{"query":"test"}' -UseBasicParsing } catch { $_.Exception.Response.StatusCode.value__ }

# 带正确密钥 → 预期 202
Invoke-WebRequest -Uri http://localhost:8000/api/task -Method Post -Headers @{"X-API-Key"="test123"} -ContentType "application/json" -Body '{"query":"test"}' -UseBasicParsing | Select-Object StatusCode
```

4. 测完把 `API_KEY=` 改回空值并重启，恢复开发模式

> 这部分在 `tests/test_api_server.py` 里已有自动化用例覆盖（`test_run_task_requires_api_key_when_configured` 等），不想手工折腾就跑第 2 层。

### ② SQL 写操作拦截

已包含在第 3 层脚本里（第 4、5 步）。

### ③ 路径穿越拦截

见第 4 层 ③。

---

## 第 7 层：服务与数据库的启停

### 一键启停（推荐）

```cmd
:: 启动两个服务 + 打开浏览器
<项目根目录>\start_all.bat

:: 停止两个服务（末尾打印端口检查结果，两行 FREE 才算停干净）
<项目根目录>\stop_all.bat
```

> ⚠️ **不要用"直接关闭两个黑窗口"来停服务。** `start_mysql.bat` 是 `mysqld --console` 前台启动，关窗口只走 Windows 控制台关闭事件，MySQL 的 fast shutdown 常常来不及跑完 —— 会在 `<MYSQL_HOME>\data` 留下脏 PID 文件与未清理的 `ibtmp1` 临时表空间，下次启动要做 InnoDB 恢复；同时 `--console` 会覆盖 `my.ini` 的 `log-error`，错误日志不落盘，关闭后的现场无从追查。
> 判断服务是否真的停了，只看端口：`netstat -ano | findstr ":3306 :8000"`，**无输出即为全停**。
>
> 若端口已无监听、浏览器却仍显示完整界面，那是**浏览器缓存的旧页面**。前端静态页现已返回 `Cache-Control: no-store`（`api/server.py` 的 `NoCacheStaticFiles`）来杜绝此问题；但在该改动之前访问过的页面需先按 `Ctrl + Shift + R` 硬刷新一次清掉旧缓存，此后 F5 即如实反映真实状态。

### MySQL

```cmd
:: 启动（双击也行，窗口保持开着）
<MYSQL_HOME>\start_mysql.bat

:: 停止（优雅关闭；会交互式提示输入 root 密码）
:: 也可以先 set MYSQL_ROOT_PWD=<你的密码> 再执行，免去每次输入
<MYSQL_HOME>\stop_mysql.bat
```

> **MySQL 不会随会话结束而停止。** `start_mysql.bat` 是前台进程，但关闭它的窗口并不可靠（见上方警告），所以停服务请用 `stop_all.bat` 或 `<MYSQL_HOME>\stop_mysql.bat`。
> 想让它开机自启：**右键 `<MYSQL_HOME>\install_service_admin.bat` → 以管理员身份运行**（注册为 `MySQL84` 服务后即为常驻服务，用 `net stop MySQL84` 停止）。

### API 服务

```cmd
cd /d "<项目根目录>"
%PY% -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --log-level info
```

- **停止**：在这个运行窗口按 `Ctrl+C` 优雅退出。**不要点窗口右上角的 X** —— 关闭控制台可能只杀掉 cmd，python 进程会继续占着 8000，下次启动就报 `address already in use`
- `--log-level info` 一定要加：不加只能看到 WARNING 级日志，智能体的每步执行记录全看不见
- 改代码后想自动重启，改用 `%PY% api\server.py`（内部带 `reload=True`）

**端口被占时**：

```cmd
netstat -ano | findstr :8000
taskkill /F /PID <上面查到的PID>
```

---

## 第 8 层：常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `pytest` 报找不到用例 | 必须在 `<项目根目录>` 目录下执行（`pytest.ini` 里写的是相对路径 `tests`） |
| 测试一片红，报连接错误 | 第 2 层正常不会连外部服务；若报错请贴完整输出。第 3 层才需要 MySQL 在跑 |
| 端到端任务返回 `Content Exists Risk` | DeepSeek 服务端内容审核拦截，不是项目问题。换中性表述重问，或刷新页面开新会话 |
| 任务长时间没结果 | 智能体需要多轮搜索，1-3 分钟正常。超过 5 分钟看服务窗口日志 |
| 服务窗口无 info 日志 | 启动命令漏了 `--log-level info` |
| `mysql.connector` 相关崩溃 | 已知问题，`db_tools.py` 已强制 `use_pure=True` 规避；若仍出现请报告 |
| VS Code 测试面板扫不到用例 | 确认解释器选对、已装 Python 扩展，然后点 Refresh Tests |

---

## 第 9 层：完整回归清单（建议按顺序）

| # | 操作 | 预期 |
|---|---|---|
| 1 | `%PY% -m ruff check --select E9,F --no-cache .` | All checks passed |
| 2 | `%PY% -m pytest` | 42 passed |
| 3 | `netstat -ano \| findstr :3306` | 有 LISTENING（MySQL 在跑） |
| 4 | `%PY% -u db_setup\test_db_tools_live.py` | 三个工具正常 + 两道拦截生效 |
| 5 | 浏览器开 `http://localhost:8000/docs` | 200，接口文档可交互 |
| 6 | 演示页提数据库问题 | 时间线显示调度数据库子智能体，返回真实数据 |
| 7 | 演示页要求生成报告 | `output\session_<thread_id>\` 下出现文件，页面可下载 |
| 8 | `%PY% -u db_setup\e2e_db_test.py` | 打印 TASK_RESULT 及分析 |

第 1-4 步不消耗 API 额度，第 6-8 步会真实调用 DeepSeek / Tavily。
