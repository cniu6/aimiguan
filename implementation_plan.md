# 实施方案 - Aimiguan (AI 安全运营平台)

## 目标描述
构建 **Aimiguan**，一个 AI 驱动的安全运营平台，包含两大核心模块：**防御监控**（通过交换机/HFish实现实时封禁）和 **主动探测**（基于 Nmap 的资产扫描）。
系统使用 **Python (FastAPI)** 作为后端，**SQLite** 作为中间存储，**Vue 3** 作为前端。

## 需要用户确定的事项 (User Review Required)
> [!IMPORTANT]
> - **外部依赖**:
>   - `python-nmap`: 需要宿主机安装 Nmap 工具。
>   - 交换机控制: 需要通过 Telnet/SSH 访问交换机的网络权限。
>   - 本地 LLM: 需要运行推理服务 (如 Ollama/LocalAI) 或可访问的 API。
>   - **人工确认机制**: 防御动作需经 AI 分析后，由管理员在 Web 端确认执行 (Human-in-the-loop)。

## 拟定变更 (Proposed Changes)

### 后端 (Python/FastAPI)
目录结构: `/backend`
#### [新建] `main.py`
- 程序入口，生命周期事件（数据库初始化），CORS 配置。

#### [新建] `core/database.py`
- SQLite 连接字符串 `sqlite:///aimiguard.db`。
- 模型定义：
    - `ThreatEvent`: 威胁事件 (包含 AI 评分 `risk_score`, AI 建议 `ai_suggestion`, 状态 `status`: PENDING/APPROVED/REJECTED)。
    - `ScanTask`, `Asset`, `BlockLog`.

#### [新建] `api/`
- `auth.py`: JWT 登录接口, RBAC 权限控制。
- `defense.py`: 
    - 接收 HFish 告警。
    - **获取待处置事件列表 (Pending Events)**。
    - **执行处置动作 (Approve/Reject)** -> 触发交换机封禁。
- `scan.py`: 资产管理, 扫描任务触发接口。
- `report.py`: AI 分析生成, 报告导出接口。

#### [新建] `services/ai_engine.py` (核心 AI 逻辑)
- **Prompt 设计**:
    1.  **风险评估 Prompt**:
        ```text
        你是一个网络安全专家。
        输入：攻击者IP={ip}, 攻击类型={attack_type}, 攻击频率={count}/min, 历史行为={history}
        任务：评估该IP的风险等级(0-100)
        输出格式：{"score": 85, "reason": "高频暴力破解且在历史黑名单中", "action_suggest": "BLOCK"}
        ```
    2.  **扫描分析 Prompt**:
        ```text
        输入：Nmap扫描结果XML/JSON
        任务：识别高危端口与潜在漏洞，给出修复建议。
        输出：Markdown格式的分析报告。
        ```
- **模型适配**: 封装 `LocalLLMClient` (支持 Ollama/LocalAI API)。
- **决策逻辑**: 
    - `Risk Score >= 80` -> 建议 BLOCK (自动推送到待办列表)
    - `Risk Score < 80` -> 建议 MONITOR (观察)

#### [新建] `services/mcp_client.py` (MCP 客户端集成)
- **功能**: 调用现有的 MCP 工具执行交换机操作。
- **通信方式**: `stdio` (子进程) 或 `SSE` (HTTP)。
- **指令调用**:
    - `use_mcp_tool(server_name, tool_name="block_ip", arguments={"ip": "1.2.3.4"})`
- **执行流程**:
    1.  接收封禁任务 (IP)。
    2.  构造 MCP 工具调用请求。
    3.  发送给 MCP Server (您现有的工具)。
    4.  解析 MCP 返回结果。
    5.  记录操作日志到 Database。
- `ai_engine.py`: LLM 集成模块，用于风险评分和报告生成。

#### [新建] `services/scanner.py` (扫描任务队列)
- **调度机制**: 由于 Nmap 扫描耗时较长，通过 `asyncio.create_task` 或简单的任务队列管理扫描任务。
- **扫描参数**: 仅支持常用命令组合 (如 `-sS -sV -p 1-65535`)，避免复杂命令注入。
- **结果处理**:
    1.  解析 Nmap XML 输出 (使用 `python-nmap` 库)。
    2.  提取 `<host>`, `<port>`, `<service>`, `<script>` (漏洞信息)。
    3.  结构化存入 `ScanResult` 表。
    4.  触发 AI 分析 (生成修复建议)。

### 前端 (Vue 3 + Vite)
目录结构: `/frontend`
#### [新建] `src/router/index.ts`
- Hash 模式路由 `createWebHashHistory()`。

#### [新建] `src/views/`
- `DefenseDashboard.vue`: 实时威胁情报流。
- `ScanManager.vue`: 资产列表, 扫描结果展示。
- `AICenter.vue`: AI 对话与报告中心。

#### [新建] `src/components/`
- Shadcn-vue & AI-Elements-vue 组件集成。

### 基础设施
#### [新建] `requirements.txt`
- `fastapi`, `uvicorn`, `python-nmap`, `sqlalchemy`, `pydantic`.

## 验证计划 (Verification Plan)

### 自动化测试
- **后端测试**: 使用 `pytest` 测试 API 端点和业务逻辑 (Mock Nmap 和 交换机连接)。
- **前端测试**: 组件渲染测试。

### 人工验证
1.  **防御流程 (Human-in-the-loop)**: 
    - 模拟 HFish 告警 -> 写入 SQLite。
    - 触发 AI 分析 -> 生成评分和建议 -> 状态置为 `PENDING`。
    - **Web 端显示待办事项** -> 用户点击“封禁” -> API 更新状态 -> 触发交换机封禁命令。
2.  **扫描流程**: 添加 localhost 资产 -> 触发扫描 -> 检查 Nmap 解析结果 -> 验证 AI 报告生成。
3.  **UI 验证**: 检查 Hash 路由导航和组件样式是否统一。
