"""
api/server.py 冒烟测试：FastAPI TestClient 验证核心接口行为，
Agent 执行已 mock，不依赖任何外部服务。
"""
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.server as server_module

PROJECT_ROOT = Path(server_module.__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"
TEST_SESSION_DIR = OUTPUT_DIR / "test_ci_session"


@pytest.fixture()
def client(monkeypatch):
    # mock 掉 Agent 执行（避免真实调用 LLM）
    async def _fake_run(query, session_id):
        return None

    monkeypatch.setattr(server_module, "run_deep_agent", _fake_run)
    with TestClient(server_module.app) as c:
        yield c


@pytest.fixture()
def sample_output_file():
    # 准备一个 output 目录下的样例文件
    TEST_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    f = TEST_SESSION_DIR / "demo.md"
    f.write_text("# 演示文件\n测试内容", encoding="utf-8")
    yield f
    shutil.rmtree(TEST_SESSION_DIR, ignore_errors=True)


@pytest.fixture()
def cleanup_upload_dir():
    # 上传测试会在 updated/ 下建会话目录，结束后清理，避免污染工作区
    target = PROJECT_ROOT / "updated" / "session_upload-test"
    yield
    shutil.rmtree(target, ignore_errors=True)


def test_run_task_returns_thread_id(client):
    resp = client.post("/api/task", json={"query": "测试任务"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "started"
    assert body["thread_id"]


def test_run_task_dev_mode_without_api_key(client, monkeypatch):
    # 开发模式：未设置 API_KEY 环境变量时接口直接放行
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/api/task", json={"query": "测试任务"})
    assert resp.status_code == 200


def test_run_task_requires_api_key_when_configured(client, monkeypatch):
    # 设置 API_KEY 后：无密钥 → 401；密钥错误 → 401；正确密钥 → 200
    monkeypatch.setenv("API_KEY", "secret-key-123")

    resp = client.post("/api/task", json={"query": "测试任务"})
    assert resp.status_code == 401

    resp = client.post("/api/task", json={"query": "测试任务"},
                       headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401

    resp = client.post("/api/task", json={"query": "测试任务"},
                       headers={"X-API-Key": "secret-key-123"})
    assert resp.status_code == 200


def test_upload_rejects_disallowed_extension(client, monkeypatch, cleanup_upload_dir):
    # 上传接口扩展名白名单：.exe 必须被拒绝
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/api/upload",
                       files={"files": ("evil.exe", b"MZ...", "application/x-msdownload")},
                       data={"thread_id": "upload-test"})
    assert resp.status_code == 415


def test_upload_accepts_allowed_extension(client, monkeypatch, cleanup_upload_dir):
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/api/upload",
                       files={"files": ("notes.md", "# hello", "text/markdown")},
                       data={"thread_id": "upload-test"})
    assert resp.status_code == 200
    assert resp.json()["files"] == ["notes.md"]


def test_run_task_reuses_thread_id(client):
    resp = client.post("/api/task", json={"query": "测试任务", "thread_id": "fixed-id"})
    assert resp.json()["thread_id"] == "fixed-id"


def test_list_files_ok(client, sample_output_file):
    resp = client.get("/api/files", params={"path": str(TEST_SESSION_DIR)})
    assert resp.status_code == 200
    files = resp.json()["files"]
    assert any(f["name"] == "demo.md" for f in files)


def test_list_files_rejects_path_outside_output(client):
    resp = client.get("/api/files", params={"path": str(PROJECT_ROOT)})
    assert resp.status_code == 403


def test_download_rejects_path_outside_output(client):
    resp = client.get("/api/download", params={"path": str(PROJECT_ROOT / "README.md")})
    assert resp.status_code == 403


def test_download_requires_api_key_when_configured(client, monkeypatch, sample_output_file):
    # 下载接口也在鉴权范围内：无密钥 401；查询参数 key 通过（<a> 直链场景）
    monkeypatch.setenv("API_KEY", "secret-key-123")
    resp = client.get("/api/download", params={"path": str(sample_output_file)})
    assert resp.status_code == 401
    resp = client.get("/api/download", params={"path": str(sample_output_file), "key": "secret-key-123"})
    assert resp.status_code == 200


def test_websocket_rejected_without_api_key(client, monkeypatch):
    # 服务端开启 API_KEY 后，WebSocket 连接必须携带 ?key=
    monkeypatch.setenv("API_KEY", "secret-key-123")
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/ws-auth-thread"):
            pass


def test_upload_sanitizes_path_traversal_filename(client, monkeypatch, cleanup_upload_dir):
    # 文件名含路径穿越片段时必须被清洗为纯文件名
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/api/upload",
                       files={"files": ("../evil.md", "# evil", "text/markdown")},
                       data={"thread_id": "upload-test"})
    assert resp.status_code == 200
    assert resp.json()["files"] == ["evil.md"]
    # 确认没有写到会话目录之外
    assert not (PROJECT_ROOT / "evil.md").exists()
    assert not (PROJECT_ROOT / "updated" / "evil.md").exists()


def test_download_ok(client, sample_output_file):
    resp = client.get("/api/download", params={"path": str(sample_output_file)})
    assert resp.status_code == 200
    assert resp.content.decode("utf-8").startswith("# 演示文件")


def test_websocket_ping_pong(client):
    with client.websocket_connect("/ws/ws-test-thread") as ws:
        ws.send_text("ping")
        data = ws.receive_json()
        assert data["type"] == "pong"
