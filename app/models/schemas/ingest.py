"""`POST /v1/ingest` 的请求模型（契约 §1.1）。"""

from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field, model_validator

BizType = Literal["moment", "photo", "note"]
Scope = Literal["couple", "personal"]
Action = Literal["upsert", "delete"]


class IngestRequest(BaseModel):
    """Java 在业务事务提交后异步推送的向量同步请求。"""

    trace_id: str | None = Field(default=None, max_length=64)
    biz_type: BizType = Field(description="moment=动态, photo=相册照片, note=学习笔记")
    biz_id: int = Field(description="业务主键")
    content: str | None = Field(
        default=None,
        description="ready-to-vector 文本（Java 已拼好）；action=delete 时可为空",
    )
    scope: Scope = Field(description="couple=情侣共享, personal=个人私有")
    scope_id: int = Field(description="couple 时为 coupleId，personal 时为 userId")
    action: Action = Field(default="upsert", description="upsert=新增/覆盖, delete=删除")

    @model_validator(mode="after")
    def _check_content(self) -> "IngestRequest":
        if self.action == "upsert" and not (self.content or "").strip():
            # 抛 ValueError → pydantic 收集成 ValidationError → 统一被转成 400
            raise ValueError("action=upsert 时 content 不能为空")
        return self
