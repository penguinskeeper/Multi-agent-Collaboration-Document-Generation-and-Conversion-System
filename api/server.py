import uuid
import os
import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

# Add project root to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

# Import agent runner and monitor
# 注意：agent.main_agent 导入时会初始化 main_agent，这可能需要几秒钟
from agent.main_agent import run_deep_agent
from api.monitor import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    服务启动时，获取当前运行的事件循环，并绑定到 WebSocket 管理器。
    确保后台线程能通过 run_coroutine_threadsafe 准确投递消息。
    （on_event("startup") 已被 FastAPI 弃用，改用 lifespan）
    """
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    logger.info("[Server] WebSocket Manager bound to loop: %s", id(loop))
    yield


app = FastAPI(title="DeepAgents API", lifespan=lifespan)

# 挂载输出目录，以便前端访问生成的静态文件
# 假设输出目录位于项目根目录下的 output
output_dir = project_root / "output"
output_dir.mkdir(exist_ok=True)

# 定义上传目录 updated
updated_dir = project_root / "updated"
updated_dir.mkdir(exist_ok=True)

# 配置 CORS：白名单模式，通过环境变量 API_ALLOWED_ORIGINS 配置（逗号分隔）。
# 未配置时默认只放行本机来源；生产部署到公网时务必显式设置为真实域名。
# 注：原来的 allow_origins=["*"] + allow_credentials=True 组合本身违反 CORS 规范，
#     浏览器会拒绝带凭据的通配符跨域响应——收紧白名单顺带修正了这个隐患。
_default_origins = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173"
_allowed_origins = [o.strip() for o in os.getenv("API_ALLOWED_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# API Key 校验（降级版安全加固，不引入 JWT 全套登录流程）：
# - .env 中配置 API_KEY 后，业务接口（/api/task、/api/upload、/api/files、
#   /api/download、/ws）必须携带请求头 X-API-Key 或查询参数 key，
#   防止公网部署后接口裸奔消耗 LLM/Tavily 付费额度、泄露生成文件与会话进度。
# - 未配置 API_KEY 时自动进入开发模式放行——与项目里 MySQL/RAGFlow
#   可选依赖的优雅降级设计保持一致，本地演示零配置。
# ---------------------------------------------------------------------
def verify_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    key: Optional[str] = Query(default=None),
):
    """校验 API Key：请求头 X-API-Key 或查询参数 key 二选一。
    （查询参数用于 <a> 直链下载等无法自定义请求头的场景）"""
    expected = os.getenv("API_KEY", "").strip()
    if not expected:
        return  # 开发模式：未设置密钥，直接放行
    if x_api_key != expected and key != expected:
        raise HTTPException(status_code=401, detail="无效的 API Key，请在请求头 X-API-Key 中携带正确密钥")
class TaskRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


# ---------------------------------------------------------------------
# 后台 Agent 任务引用管理：
# asyncio.create_task 的返回值若不持引用，任务可能被垃圾回收中途取消。
# 这里统一持有引用，并在任务结束时回收 + 记录未被内部捕获的异常。
# ---------------------------------------------------------------------
_background_tasks: set = set()


def _on_agent_task_done(task: asyncio.Task):
    _background_tasks.discard(task)
    if task.cancelled():
        logger.warning("[Server] 后台 Agent 任务被取消")
        return
    exc = task.exception()
    if exc:
        logger.error("[Server] 后台 Agent 任务异常: %s", exc)


def spawn_agent_task(query: str, thread_id: str):
    task = asyncio.create_task(run_deep_agent(query, thread_id))
    _background_tasks.add(task)
    task.add_done_callback(_on_agent_task_done)


@app.post("/api/task")
async def run_task(request: TaskRequest, _: None = Depends(verify_api_key)):
    # 1. [ID 初始化]
    thread_id = request.thread_id or str(uuid.uuid4())

    # 2. [后台执行] 异步运行 Agent，不阻塞主线程
    # 持有任务引用防止被 GC 回收，异常统一记录（详见 _on_agent_task_done）
    spawn_agent_task(request.query, thread_id)

    # 3. [立即响应]
    return {"status": "started", "thread_id": thread_id}


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), thread_id: str = Form(...), _: None = Depends(verify_api_key)):
    """
    文件上传接口 (File Upload)。

    目标：
    1. 接收用户上传的一个或多个文件。
    2. 保存到 `updated/session_{thread_id}` 目录。
    3. 供 Agent 在后续任务中读取和分析。

    Args:
        files (List[UploadFile]): 文件对象列表。
        thread_id (str): 关联的任务会话 ID。
    """
    # 1. [目录准备] 确保上传目录存在
    target_dir = updated_dir / f"session_{thread_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 0. [安全校验] 扩展名白名单（与 upload_file_read_tool 支持解析的类型对齐）+ 大小限制
    allowed_ext = {".md", ".docx", ".pdf", ".xlsx", ".csv"}
    max_size_mb = 20
    max_bytes = max_size_mb * 1024 * 1024
    saved_files = []
    # 1. [文件名清洗] Path.name 在 Linux 上不识别反斜杠分隔符，手动按两种分隔符取最后一段，
    #    防止 "..\\evil.md" / "../evil.md" 之类的路径穿越写入会话目录之外。
    for file in files:
        safe_name = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
        if not safe_name or safe_name in {".", ".."}:
            raise HTTPException(status_code=400, detail="非法的文件名")
        ext = Path(safe_name).suffix.lower()
        if ext not in allowed_ext:
            raise HTTPException(status_code=415, detail=f"不支持的文件类型: {ext}（允许: md/docx/pdf/xlsx/csv）")
        if (file.size or 0) > max_bytes:
            raise HTTPException(status_code=413, detail=f"文件 {safe_name} 超过 {max_size_mb}MB 大小限制")
        file.filename = safe_name

    # 2. [保存] 遍历并写入文件
    for file in files:
        file_path = target_dir / file.filename
        # 使用二进制模式写入，支持各种文件格式 (图片、PDF、文本等)
        # 分块写入并统计实际字节数：客户端可能不提供 size，写入时兜底强制限额
        written = 0
        try:
            with file_path.open("wb") as buffer:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise HTTPException(status_code=413, detail=f"文件 {file.filename} 超过 {max_size_mb}MB 大小限制")
                    buffer.write(chunk)
        except HTTPException:
            file_path.unlink(missing_ok=True)  # 清理写了一半的文件
            raise
        saved_files.append(file.filename)

    # 3. [响应] 返回成功保存的文件列表
    return {"status": "uploaded", "files": saved_files}


@app.get("/api/download")
async def download_file(path: str, _: None = Depends(verify_api_key)):
    """
    文件下载接口 (File Download)。

    目标：
    1. 根据绝对路径下载文件。
    2. 严格的安全检查，防止越权访问。

    Args:
        path (str): 文件的绝对路径 (通常从 list_files 接口获取)。
    """
    # 1. [安全检查] 路径解析与越权校验
    try:
        abs_path = Path(path).resolve()
        output_abs = output_dir.resolve()

        # 必须确保请求的文件在 output 目录下
        if not abs_path.is_relative_to(output_abs):
            raise HTTPException(status_code=403, detail="拒绝访问: 只能下载输出目录下的文件")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="无效的路径参数")
    # 2. [存在性检查]
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 3. [响应] 返回文件流 (浏览器自动触发下载)
    return FileResponse(abs_path, filename=abs_path.name)


@app.get("/api/files")
async def list_files(path: str, _: None = Depends(verify_api_key)):
    """
    文件列表查询接口 (File Explorer)。

    目标：
    1. 列出指定目录下的所有生成文件。
    2. 提供文件元数据（大小、时间、下载链接）。
    3. 严格的安全检查，防止路径遍历攻击。

    Args:
        path (str): 目标目录的绝对路径 (必须在 output 目录下)。
    """
    # 1. [调试] 记录请求路径
    logger.debug("请求文件列表: %s", path)

    try:
        # 2. [解析] 获取绝对路径对象
        abs_path = Path(path).resolve()
        output_abs = output_dir.resolve()

        # 3. [安全] 检查路径是否越界 (Path Traversal Check)
        if not abs_path.is_relative_to(output_abs):
            logger.error("拒绝访问: %s 不在 %s 目录下", abs_path, output_abs)
            raise HTTPException(status_code=403, detail="拒绝访问: 只能访问输出目录下的文件")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("路径解析失败: %s", e)
        raise HTTPException(status_code=400, detail=f"路径无效: {e}")

    # 4. [检查] 目录是否存在
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="目录不存在")

    files = []
    try:
        # 5. [遍历] 递归查找所有文件
        for file_path in abs_path.rglob("*"):
            if file_path.is_file():
                # 计算相对路径，生成下载 URL
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "type": "file",
                    "path": str(file_path),
                    # "url": f"/outputs/{url_path}",
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })

    except Exception as e:
        logger.error("遍历文件失败: %s", e)
        return {"error": str(e)}

    # 6. [排序] 按修改时间倒序排列 (最新的在前)
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    logger.debug("找到 %d 个文件", len(files))
    return {"files": files}


# 当浏览器请求 ws://localhost:8000/ws/thread_123 时：
# 1. 路由匹配 ：FastAPI 发现这个 URL 匹配了你写的 @app.websocket("/ws/{thread_id}") 。
# 2. 创建对象 ：FastAPI (基于 Starlette) 会立刻在 主事件循环 中实例化一个 WebSocket 对象。
#    - 这个对象封装了底层的 TCP 连接、HTTP 握手信息、以及后续的消息收发方法 ( send_text , receive_text 等)。
# 3. 注入参数 ：FastAPI 自动把这个刚创建好的 WebSocket 对象，作为参数传给你的 websocket_endpoint(websocket, ...) 函数。
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str, key: Optional[str] = Query(default=None)):
    logger.info("会话向我们发起了请求，要求建立连接：%s 对应：%s", thread_id, websocket)
    """
    WebSocket 实时通讯核心接口 (Real-time Communication)。

    目标：
    1. 建立长连接，实现服务端与前端的双向通信。
    2. 绑定 `thread_id`，实现会话级消息隔离。
    3. 维持心跳 (Keep-Alive)，防止连接超时。

    执行步骤：
    1. 握手：接受 WebSocket 连接请求。
    2. 注册：将连接实例绑定到 `monitor.manager`，关联 `thread_id`。
    3. 循环：进入消息监听循环，处理前端发送的心跳或指令。
    4. 异常：捕获断开连接异常，清理资源。

    Args:
        websocket (WebSocket): WebSocket 连接实例。
        thread_id (str): 当前会话的唯一标识。
    """
    # 0. [鉴权] 与写接口一致的密钥校验（WebSocket 无法自定义请求头，走查询参数）。
    #    开发模式（未配置 API_KEY）直接放行。校验失败以 4401 关闭连接。
    expected_key = os.getenv("API_KEY", "").strip()
    if expected_key and key != expected_key:
        await websocket.close(code=4401)
        return

    # 1. [注册] 建立连接并绑定到管理器
    await manager.connect(websocket, thread_id)

    try:
        # 2. [循环] 保持连接活跃
        while True:
            # 3. [监听] 接收前端消息 (通常是 ping 心跳)
            data = await websocket.receive_text()

            # 4. [响应] 回复 pong 消息
            await websocket.send_json({
                "type": "pong",
                "message": f"服务端已收到: {data}"
            })

    except WebSocketDisconnect:
        # 5. [清理] 客户端主动断开
        manager.disconnect(websocket, thread_id)
        logger.info("[WebSocket] 客户端已断开: %s", thread_id)

    except Exception as e:
        # 6. [异常] 发生错误时断开
        logger.error("[WebSocket] 连接异常: %s", e)
        manager.disconnect(websocket, thread_id)


# ---------------------------------------------------------------------
# 前端演示页：将 static/ 目录挂载到根路径（必须放在所有 API 路由定义之后，
# FastAPI 按注册顺序匹配，API 路由优先于静态文件兜底）
# 访问 http://localhost:8000/ 即可打开聊天演示页
# ---------------------------------------------------------------------
class NoCacheStaticFiles(StaticFiles):
    """
    自定义静态文件类：强制响应携带 Cache-Control: no-store。

    为什么要这么做？
    Starlette 的 StaticFiles 默认只发送 Last-Modified 和 ETag，**不发送
    Cache-Control**。浏览器对缺少 Cache-Control 的响应会启用「启发式缓存」，
    缓存时长经验值约为 (当前时间 - Last-Modified) × 10%。这意味着 index.html
    ──本项目恰好是「7 天前修改的静态页」── 会被浏览器静默缓存十几个小时，
    期间从地址栏访问 localhost:8000 可能**一个网络请求都不发**，直接拿磁盘
    缓存渲染。

    后果：执行 stop_all.bat 停止服务后按 F5，仍然能看到完整的项目界面，
    看起来像「服务没停干净」，实际是缓存的旧页面在骗人。

    本项目是本地演示场景，全局 no-store 最省心：停止服务后刷新即可如实
    反映真实状态。仅影响浏览器缓存行为，不改变任何功能逻辑。
    """

    async def get_response(self, path, scope, *args, **kwargs):
        # *args / **kwargs 用于兼容不同 Starlette 版本（新版多一个 head 关键字参数）
        response = await super().get_response(path, scope, *args, **kwargs)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


static_dir = project_root / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", NoCacheStaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)