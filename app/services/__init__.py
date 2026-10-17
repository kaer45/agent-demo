"""业务逻辑层。

纪律：**本层禁止 import fastapi**。
好处是能单测、能在脚本里直接复用、以后换 Web 框架不用改。

副作用：`hello_agents` / `qdrant_client` 等重依赖一律**懒加载**（在客户端封装内部
首次使用时才 import），这样 mock 模式下没有这些包也能启动服务。
"""
