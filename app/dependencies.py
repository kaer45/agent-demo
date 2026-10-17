"""FastAPI 依赖：目前只有一个 —— 校验 Java 侧传来的 X-Agent-Key。"""

from __future__ import annotations

import logging

from fastapi import Header
from app.core.errors import unauthorized, AgentError

from app.config import get_settings
from app.core.errors import unauthorized

logger = logging.getLogger(__name__)


async def verify_key(x_agent_key: str | None = Header(default=None, alias="X-Agent-Key")):
    settings = get_settings()
    if not settings.agent_key:
        raise AgentError("服务端未配置 AGENT_KEY", status_code=500)
    if x_agent_key != settings.agent_key:
        raise unauthorized()  # 返回 401 信封