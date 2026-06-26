# pythonAI

5 个月 AI 应用工程师学习仓库：chat-api → 储能 RAG → 故障诊断 Agent。

## 项目

| 目录 | 说明 | 文档 |
|------|------|------|
| [`fastapi_demo/`](fastapi_demo/) | **chat-api** — LLM 聊天后端（鉴权 / PG / Redis / Docker） | [README v1.0](fastapi_demo/README.md) |
| `docs/` | 学习计划与笔记 | [5MONTH_PLAN.md](docs/5MONTH_PLAN.md) |

## 快速体验 chat-api

```bash
cd fastapi_demo
docker compose up -d --build
./scripts/smoke_test.sh
```

详细步骤见 [fastapi_demo/README.md](fastapi_demo/README.md)。
