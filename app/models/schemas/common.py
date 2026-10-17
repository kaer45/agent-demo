"""与 Java `Result<T>` 对齐的响应信封（主要用于 OpenAPI 文档展示）。"""
from __future__ import annotations
from typing import Any

from pydantic import BaseModel, Field


class ResultEnvelope(BaseModel):
    code: int = Field(default=0, description="0 表示成功，非 0 表示失败")
    message: str = Field(default="success", description="人类可读信息")
    data: Any | None = Field(default=None, description="业务数据")


class SummarizeData(BaseModel):
    summary: str = Field(description="摘要正文，必填且非空白（Java 会校验）")