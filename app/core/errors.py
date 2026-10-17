"""统一错误模型与 Result 信封。

为什么必须有这一层（契约 §1.2）：
    Java 对 `/v1/ingest` **只看 HTTP 状态码，不看 body.code**。
    所以 Python 内部出错时必须返回非 200，否则 Java 会认为成功、不重试，
    数据静默丢失且没有任何报错。

对外响应一律是 `{code, message, data}`，与 Java 的 `Result<T>` 对齐。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def ok(data: Any = None, message: str = "success") -> dict:
    """成功响应体（HTTP 200）。"""
    return {"code": 0, "message": message, "data": data}


class AgentError(Exception):
    """业务异常。`status_code` 决定 HTTP 状态，`code` 决定 body.code。"""

    def __init__(self, message: str, status_code: int = 500, code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = status_code if code is None else code


def bad_request(message: str) -> AgentError:
    return AgentError(message, status_code=400, code=400)


def unauthorized(message: str = "invalid agent key") -> AgentError:
    return AgentError(message, status_code=401, code=401)


def unavailable(message: str) -> AgentError:
    """依赖能力未就绪（模型 / 向量库不可用）。503 表示「暂时不可用、可重试」。"""
    return AgentError(message, status_code=503, code=503)


def upstream_error(what: str, exc: BaseException) -> AgentError:
    """把第三方异常翻译成统一的 500。原始堆栈只进日志，不进响应体。"""
    logger.exception("%s: %s", what, exc)
    return AgentError(what, status_code=500, code=500)


def _summarize_validation(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors()[:5]:
        loc = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body", "__root__"))
        parts.append(f"{loc or 'body'}: {err.get('msg', 'invalid')}")
    return "; ".join(parts) or "invalid request"


def register_exception_handlers(app: FastAPI) -> None:
    """把所有异常收敛成统一的 `{code, message, data}` 信封。"""

    @app.exception_handler(AgentError)
    async def _agent_error(request: Request, exc: AgentError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("请求失败(%s): %s", exc.status_code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # FastAPI 默认返回 422；Java 会把 422 当失败并重试 3 次（契约 §5 里只有 400），
        # 所以这里统一转成 400。
        detail = _summarize_validation(exc)
        logger.warning("参数校验失败: %s", detail)
        return JSONResponse(
            status_code=400,
            content={"code": 400, "message": f"参数错误: {detail}", "data": None},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": "内部错误", "data": None},
        )
