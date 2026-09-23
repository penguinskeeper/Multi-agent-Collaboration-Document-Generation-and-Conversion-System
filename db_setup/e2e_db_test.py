"""端到端验证：提交数据库查询任务，通过 WebSocket 接收实时事件"""
import asyncio
import json
import urllib.request

QUERY = "请查询数据库中销售额最高的 5 种药品，给出药品名称、分类和销售额，并简单分析一下。不要生成文件。"


async def main() -> None:
    import websockets

    req = urllib.request.Request(
        "http://localhost:8000/api/task",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tid = json.loads(urllib.request.urlopen(req, timeout=30).read())["thread_id"]
    print("THREAD:", tid, flush=True)

    async with websockets.connect(f"ws://localhost:8000/ws/{tid}") as ws:
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=180)
                ev = json.loads(msg)
                if ev.get("type") != "monitor_event":
                    continue
                kind, text = ev.get("event"), ev.get("message", "")
                if kind == "task_result":
                    print("TASK_RESULT:")
                    print(str(ev.get("data", {}).get("result", ""))[:1500], flush=True)
                    break
                if kind == "error":
                    print("ERROR:", text, flush=True)
                    break
                print(f"[{kind}] {text[:100]}", flush=True)
        except asyncio.TimeoutError:
            print("TIMEOUT_NO_RESULT", flush=True)


asyncio.run(main())
