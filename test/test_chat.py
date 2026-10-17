"""测 /v1/chat 带检索。"""

import httpx

BASE = "http://127.0.0.1:8001"
HEADERS = {"X-Agent-Key": "change-me"}


def chat(message: str, scope: str = "couple", scope_id: int = 11) -> None:
    print(f"\n>>> {message}")
    with httpx.stream(
        "POST",
        f"{BASE}/v1/chat",
        headers=HEADERS,
        json={
            "trace_id": "a1b2c3d4e5f60718",
            "user_id": 1,
            "couple_id": 11,
            "session_id": "couple11",
            "message": message,
            "scope": scope,
            "scope_id": scope_id,
        },
        timeout=60,
    ) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                print(line)


if __name__ == "__main__":
    # 先确认 seed 数据在 Qdrant 里
    chat("我们上次爬山看到了什么？", scope="couple", scope_id=11)
    chat("Redis 是什么？", scope="personal", scope_id=1)
    chat("今天天气怎么样？", scope="couple", scope_id=11)  # 应该召回不到