# D29 · chat-api 录屏 5 分钟演示稿

> **学习目标**：录一段 5 分钟视频，演示 chat-api 能跑、链路能讲清。  
> **验收标准**：脱稿或半脱稿讲完「请求从进入到返回」的全路径；画面里能看到启动、调接口、日志、缓存对比。  
> **关联文档**：[fastapi_demo/README.md](../fastapi_demo/README.md)

---

## 一、录屏前准备（约 10 分钟）

### 环境

- [ ] Docker Desktop 已启动
- [ ] 终端字体放大（建议 16–18pt），录屏时能看清命令
- [ ] 关闭无关通知（微信、邮件、系统弹窗）
- [ ] 提前跑通一遍，避免录到一半报错：

```bash
cd fastapi_demo
docker compose up -d --build
docker compose ps          # 三个服务 healthy
./scripts/smoke_test.sh    # 全部 PASS
```

### 录屏工具（任选）

| 工具 | 说明 |
|------|------|
| macOS 自带 | `Cmd + Shift + 5` → 录制所选部分 |
| OBS | 免费，可录终端 + 浏览器分屏 |
| QuickTime | 新建屏幕录制 |

建议：**终端全屏** 或 **终端 70% + 浏览器 30%**（`/docs` 或架构图）。

### 开场前状态

```bash
# 建议录之前清屏，画面干净
clear
cd fastapi_demo
```

---

## 二、5 分钟时间轴（照着讲）

总时长 **4:30–5:30** 均可。下面按 **5:00** 切分。

| 时间 | 环节 | 你讲什么 | 你做什么 |
|------|------|----------|----------|
| **0:00–0:30** | 开场 | 项目名、技术栈、解决什么问题 | 展示 README 标题或目录树 `ls` 一眼 |
| **0:30–1:30** | 架构 | 三层服务 + 一条 chat 链路 | 指 README 架构图，或口头画：Client → FastAPI → PG/Redis/LLM |
| **1:30–2:30** | 启动验证 | 一键部署、健康检查 | `docker compose ps` → `curl /healthz` |
| **2:30–4:00** | 核心演示 | 鉴权、聊天、缓存、历史 | 见下方「第三节命令脚本」 |
| **4:00–4:45** | 日志讲链路 | request_id、cache_hit、各阶段耗时 | `docker compose logs -f web` 指 `[PERF]` 行 |
| **4:45–5:00** | 收尾 | 冒烟测试 + Phase 0 小结 | `./scripts/smoke_test.sh` 全绿 → 说下周 RAG |

---

## 三、演示命令脚本（复制到终端）

录 **2:30–4:00** 时段时，建议提前贴好或分段输入。

### 3.1 健康检查（1:30–2:00）

```bash
curl -s http://127.0.0.1:8000/ping | python3 -m json.tool

curl -s http://127.0.0.1:8000/healthz | python3 -m json.tool
```

**口播要点**：

> healthz 同时检测应用、PostgreSQL 和 Redis。任意一项挂了会返回 503，方便 K8s 或 Docker 做探活。

---

### 3.2 鉴权失败（2:00–2:20）

```bash
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","session_id":"sess_demo_001","message":"你好"}' \
  | python3 -m json.tool
```

**口播要点**：

> 没带 Bearer Token，路由层直接 401，请求不会进业务和 LLM，这是第一层门禁。

---

### 3.3 首次聊天 — cache miss（2:20–3:10）

```bash
export TOKEN="mytoken123456"

curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","session_id":"sess_demo_001","message":"储能BMS是什么"}' \
  | python3 -m json.tool
```

**口播要点（链路核心，必讲）**：

> 请求进来以后走四层：  
> 1. **Router** — Bearer 鉴权  
> 2. **Pydantic** — 参数校验、输入规范化  
> 3. **Service** — 先查 Redis，未命中再调 LLM，同时写 PostgreSQL  
> 4. **返回** — `from_cache: false` 表示这次走了模型  

---

### 3.4 第二次相同问题 — cache hit（3:10–3:40）

```bash
# 完全相同的消息再发一次
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","session_id":"sess_demo_001","message":"储能BMS是什么"}' \
  | python3 -m json.tool
```

**口播要点**：

> 第二次 `from_cache: true`，Redis 命中，跳过 LLM，延迟明显更低。相同问题靠 MD5 做缓存 key，TTL 默认 30 分钟。

---

### 3.5 查历史（3:40–4:00）

```bash
curl -s "http://127.0.0.1:8000/history?user_id=u001&page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

**口播要点**：

> 每次问答都会落库 `chat_messages`，支持按 user_id 分页查历史，msg_status 区分成功、失败和处理中。

---

### 3.6 性能日志（4:00–4:45）

另开一个终端，或录之前开好：

```bash
docker compose logs --tail=30 web
```

找到类似一行：

```text
[PERF] path=/chat | method=POST | status=200 | total_ms=... | cache_hit=True/False | cache_ms=... | llm_ms=... | db_ms=... | request_id=req_xxx
```

**口播要点**：

> 每条请求有唯一 request_id，PERF 行把 cache、LLM、DB 耗时拆开，面试或排障时一眼能看出瓶颈在哪。

---

### 3.7 收尾冒烟（4:45–5:00）

```bash
./scripts/smoke_test.sh
```

**口播要点**：

> 12 条自动化回归覆盖鉴权、校验、缓存和历史。Phase 0 chat-api 封板，下个月做储能 RAG。

---

## 四、口播稿（精简版，可打印）

```
【开场 30s】
大家好，这是我学习计划第 1 个月的项目 chat-api。
用 FastAPI 做了一个可调 LLM 的后端，带鉴权、PostgreSQL 存历史、Redis 做回答缓存，
Docker Compose 一键启动三个服务。

【架构 60s】
整体是 Client 调 FastAPI，后面挂 PostgreSQL、Redis 和 LLM。
一条聊天请求的链路是：
鉴权 → 参数校验和脱敏 → 查 Redis → 未命中则调 LLM → 写库 → 返回。
命中缓存就直接用 Redis 里的答案，省钱也更快。

【启动 60s】
docker compose 起 app、postgres、redis。
healthz 返回 app、postgres、redis 都是 ok，说明全链路依赖正常。

【演示 90s】
先不带 Token，401，进不了业务。
带 Token 第一次问「储能 BMS 是什么」，from_cache false，走了模型。
同样问题再问一次，from_cache true，缓存命中。
然后 history 接口能分页查到刚才的记录。

【日志 45s】
看 web 容器日志，PERF 行有 request_id、cache_hit、
cache_ms、llm_ms、db_ms，一次请求全链路可追踪。

【收尾 15s】
跑 smoke_test 全部通过。chat-api Phase 0 完成，下一步做储能知识库 RAG。
```

---

## 五、链路讲解图（录屏时可切到 README）

录架构段时，可打开 `fastapi_demo/README.md` 滚动到 **「请求链路」** Mermaid 图，或用下面文字版：

```text
POST /chat
    │
    ├─① verify_token        → 无 Token → 401
    │
    ├─② ChatRequest 校验    → 超长/空 → 400
    │
    ├─③ sensitive_filter    → 敏感词 → 400
    │
    ├─④ Redis get           → HIT  → 写 PG → 返回 from_cache=true
    │                       → MISS ↓
    │
    ├─⑤ PG 插入「处理中」
    │
    ├─⑥ call_llm            → 超时重试 2 次
    │
    ├─⑦ Redis set + PG 更新
    │
    └─⑧ 返回 from_cache=false
```

**三层拦截**（可选 15 秒补充）：

| 层 | 拦什么 |
|----|--------|
| Pydantic | 长度、类型 |
| Service | 空值、敏感词 |
| 缓存层 | 空回答/失败短 TTL，避免打爆模型 |

---

## 六、加分项（时间充裕再做）

- 打开 http://127.0.0.1:8000/docs 点一下 `POST /chat` Try it out
- 提一句敏感词拦截：`message` 含违规词直接 400
- 指一下 `docker compose.yml` 里三个 healthcheck

**不要录**：念大段代码、逐文件翻源码、超过 6 分钟。

---

## 七、常见问题

| 问题 | 处理 |
|------|------|
| `curl: connection refused` | `docker compose up -d`，等 healthy |
| LLM 超时 | 网络问题，录前多测一次；口播说「演示环境用 postman-echo」 |
| 缓存一直是 false | 两次 message 必须完全一致（含空格） |
| 录屏没声音 | 录前试麦；macOS 录屏选项里勾选麦克风 |
| 超过 5 分钟 | 砍掉 Swagger、敏感词演示，保留 healthz + chat×2 + history + smoke |

---

## 八、录完自检

- [ ] 时长 4:30–5:30
- [ ] 提到了 **鉴权 → 校验 → 缓存 → LLM → 数据库**
- [ ] 画面里出现过 `from_cache: false` 和 `from_cache: true`
- [ ] 提到过 `request_id` 或 `[PERF]` 日志
- [ ] `smoke_test.sh` 结尾全 PASS（或说明已知 skip 原因）
- [ ] 视频已保存/上传（本地命名建议：`D29-chat-api-demo-YYYYMMDD.mp4`）

---

## 九、打卡模板

```text
日期：D29
学什么（40m）：演示型技术分享结构 / 5 分钟答辩节奏
做了什么（70m）：录制 chat-api 全链路演示视频
验收是否通过：是 / 否
视频路径：
笔记链接：docs/D29-chat-api-录屏稿.md
明日优先级：D30 月复盘 + 列第 2 月 RAG 任务
```

---

## 十、与学习计划对照

| 计划项 | 本稿对应 |
|--------|----------|
| D29 录屏 5min | 第二节时间轴 + 第三节命令 |
| 演示 chat-api | 健康检查 + chat + history + smoke |
| 能讲清链路 | 第四节口播稿 + 第五节链路图 |
| Phase 0 封板（D30 前） | 录完即完成月 1 倒数第二项交付 |
