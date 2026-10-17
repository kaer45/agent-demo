"""`POST /v1/chat` 的请求模型"""

from __future__ import annotations
from typing import Literal
from pydantic import Field,BaseModel,model_validator

# 定义类型，只能是其中的参数
Scope=Literal["couple","personal"]

# 继承BaseModel，可以进行参数校验和序列化
class ChatRequest(BaseModel):
    trace_id: str | None = Field(default=None, max_length=64)
    user_id: int | None = Field(default=None, description="发起提问的用户")
    couple_id: int | None = Field(default=None, description="scope=couple 时的情侣空间 id")
    session_id: str = Field(
        max_length=128,
        description="Java 生成：聊天内 @bot → couple{coupleId}；/ai 页 → user{userId}",
    )
    message: str = Field(description="用户输入（@bot 后的完整文本）")
    scope: Scope = Field(default="couple")
    scope_id: int | None = Field(default=None, description="检索时用于隔离的域 id")

    @model_validator(mode="after")
    def _fill_scope_id(self) -> "ChatRequest":
        # Java 一定会传 scope_id；这里兜底，避免下游检索拿到 None
        if self.scope_id is None:
            self.scope_id = self.couple_id if self.scope == "couple" else self.user_id
        if not self.message.strip():
            raise ValueError("message 不能为空白")
        return self