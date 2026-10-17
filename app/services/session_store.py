"""基于 SQLite 的多轮会话历史存储（契约 §2.3）。

表结构：
    chat_history(id, session_key, role, content, created_at)

设计要点：
1. session_key = f"{user_id}:{session_id}"，不同用户/会话严格隔离。
2. 读取时按 id 倒序取最近 N*2 条（N 轮 = N 条 user + N 条 assistant），
   Python 里再 reversed() 恢复正序。
3. 写入用 finally 保证：即使流式中断，已产出的内容也不丢。
4. TTL 清理暂时不自动做，留 cleanup() 给定时任务或启动时调用。
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------

@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    """每次操作用一个新连接（SQLite 推荐做法，避免多线程共用 conn）。"""
    s = get_settings()
    conn = sqlite3.connect(s.sqlite_file)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """建表。幂等，可重复调用。"""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_history_session
            ON chat_history(session_key, id)
        """)
    logger.info("SQLite 会话表就绪: %s", get_settings().sqlite_file)


# ---------------------------------------------------------------------------
# 读写
# ---------------------------------------------------------------------------

def history(session_key: str, max_turns: int) -> list[dict[str, str]]:
    """读最近 max_turns 轮历史，按时间正序返回。

    返回格式：[{"role": "user", "content": "..."}, {"role": "assistant", ...}, ...]
    每轮 = 1 条 user + 1 条 assistant，所以最多取 max_turns*2 条。
    """
    if max_turns <= 0:
        return []

    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM chat_history
            WHERE session_key = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_key, max_turns * 2),
        ).fetchall()

    # DESC 取的是最近的，但要按时间正序发给模型，所以 reversed
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def append(session_key: str, role: str, content: str) -> None:
    """追加一条消息。"""
    if not content:
        return
    with _conn() as conn:
        conn.execute(
            "INSERT INTO chat_history(session_key, role, content) VALUES (?, ?, ?)",
            (session_key, role, content),
        )


def cleanup(ttl_hours: int) -> int:
    """删除超过 ttl_hours 的记录，返回删除条数。

    暂不自动调用，留接口给启动时或定时任务。
    """
    if ttl_hours <= 0:
        return 0
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM chat_history WHERE created_at < datetime('now', ?)",
            (f"-{ttl_hours} hours",),
        )
        return cur.rowcount