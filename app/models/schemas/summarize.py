"""`POST /v1/summarize` 的请求模型（契约 §3.1）。"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator


class SummarizeRequest(BaseModel):
    trace_id: str = Field(default=None, max_length=64)
    user_id: int | None = None
    note_id: int | None = None
    title: str | None = Field(default=None, max_length=500)
    content: str = Field(
        description="抽取出的笔记正文全文（Java 侧上限 20 万字，Python 自行截断/分段）"
    )

    @field_validator("content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("content 不能为空白")
        return value
