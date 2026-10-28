# AI 旅游规划平台

基于 FastAPI + LangGraph + Redis + MySQL + Vue3 的智能旅游规划平台。通过多节点 LangGraph 工作流(需求解析 → 行程生成 → 预算建议 → 方案汇总)生成完整旅行方案。

## 目录结构

```
travel-planner/
├── backend/            # FastAPI 后端
│   ├── main.py         # 入口,启动:uvicorn main:app --reload
│   ├── graph.py        # LangGraph 规划工作流
│   ├── database.py     # MySQL 连接(自动建库建表)
│   ├── redis_client.py # Redis 会话缓存
│   ├── models.py       # 数据表模型
│   └── routers/        # 接口:对话、历史方案
└── frontend/           # Vue3 + Vite 前端
```

## 前置条件

1. 本地已启动 **MySQL**(默认 `root:123456@localhost:3306`,可通过 `MYSQL_URL` 修改)
2. 本地已启动 **Redis**(默认 `localhost:6379`,可通过 `REDIS_URL` 修改)
3. 已配置环境变量 **OPENAI_API_KEY**(阿里百炼 Key)

## 启动步骤

### 方式一:一键启动(推荐)

```powershell
cd travel-planner
pip install -r backend\requirements.txt
$env:OPENAI_API_KEY="sk-你的百炼Key"   # 或在 backend/.env 中配置
python app.py
```

`app.py` 会自动判断:

- **首次运行**(无 `frontend/dist`):自动 `npm install` 并启动 Vite 开发服务器 + 后端,打开 http://localhost:5173
- **已执行过 `npm run build`**:FastAPI 单端口托管前后端,打开 http://localhost:8000

### 方式二:手动分别启动

**后端**:

```powershell
cd travel-planner\backend
pip install -r requirements.txt
uvicorn main:app --reload
```

后端运行在 http://localhost:8000 ,接口文档:http://localhost:8000/docs

**前端**:

```powershell
cd travel-planner\frontend
npm install
npm run dev
```

打开 http://localhost:5173 ,输入如"我想去云南玩 5 天,预算 5000,喜欢美食和摄影"即可生成方案。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `OPENAI_API_KEY` | (必填) | 阿里百炼 API Key |
| `OPENAI_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | OpenAI 兼容接口地址 |
| `MODEL_NAME` | `qwen-plus` | 模型名称 |
| `MYSQL_URL` | `mysql+pymysql://root:123456@localhost:3306/travel_planner?charset=utf8mb4` | MySQL 连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |

## 数据存储

- **MySQL**:持久化对话消息(`chat_messages`)与旅行方案(`travel_plans`),首次启动自动建库建表
- **Redis**:缓存会话上下文(7 天过期),用于多轮对话
