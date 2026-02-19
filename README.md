# Aimiguan

> 本文档是项目唯一主文档（Single Source of Truth）。
> 架构、流程、数据模型、实施计划、验证与里程碑均以本 README 为准。

## 文档导航
- 产品定位与目标
- 架构约束、接口规范、用户确认事项
- 拟定变更（后端/前端/服务/测试）
- 主流程、模块拆分、AI 强化、模型策略
- 数据模型、验证计划、里程碑与实施建议
- 运维手册、风险边界、后续演进

## 当前仓库状态
- 当前仓库以“实施方案与架构文档”作为第一阶段产物。
- 代码骨架尚未完全落地，建议按本 README 的“拟定变更 + 里程碑”顺序推进。
- 文档中的目录与文件路径采用目标结构描述（便于后续按章节实施）。

## 产品定位
`Aimiguan` 是一个 AI 驱动的自动化安全运营产品，分为两大板块：`防御监控` 与 `探测扫描`。

核心价值：
- 防御监控：对威胁事件进行实时处置（封禁、观察、回滚）
- 探测扫描：主动调用 Kali/MCP/漏洞工具扫描目标资产并输出风险清单
- AI 中枢：统一做设备管理、自然对话、风险评分、策略建议、分析报告生成
- 异常推送：支持多通道异常通知与机器人联动
- 插件扩展：支持 MCP 第三方插件接入（如 bot）
- 全流程可审计、可追溯、可复盘

## 项目目标
本项目当前目标是实现一个基于 `agent` 的安全联动系统：
- 从黑名单数据 API、蜜罐、扫描器获取威胁与漏洞数据
- 使用 `SQLite` 作为临时数据中间缓存（事件、任务、扫描结果）
- 由 Python 从 `SQLite` 读取任务并执行封禁/扫描编排
- 通过自研 MCP tools 控制多台交换机，在 `tele` 端口按逻辑顺序封禁指定 IP
- 主动调用 Kali/MCP/漏洞工具对目标主机进行探测扫描
- 在 Web 端展示 AI 对话、AI 分析、AI 报告与执行总结
- 预留外部防火墙 API 对接能力，将高风险 IP 同步下发到外部防火墙封堵

## 技术架构约束（固定）
- 后端：`Python`
- 数据中间缓存：`SQLite`
- 前端：`Vue`
- 前后端分离：采用前后端完全分离部署，前端通过统一 `/api/` 前缀访问后端
- 前端路由模式：`Hash` 模式（`#/`），避免服务端路由回退配置复杂度
- 组件库（统一使用）：
  - `https://www.ai-elements-vue.com/`
  - `https://www.shadcn-vue.com/`
- 约束说明：后续前端组件优先复用以上两套组件库，不再引入新的主组件库，确保界面风格统一与开发效率。

## 范围与边界
### 本期范围（In Scope）
- 防御监控闭环：威胁采集 -> AI 评分 -> 人工审批 -> 交换机执行 -> 审计留痕。
- 探测扫描闭环：资产管理 -> 扫描调度 -> 结果解析 -> AI 报告 -> 导出归档。
- AI 中枢能力：对话、分析、报告、TTS（本地优先模型策略）。
- 外部联动能力：MCP 插件接入、异常推送、外部防火墙同步封堵。

### 非目标（Out of Scope, 当前阶段）
- 大规模分布式集群调度与跨地域多活。
- 全量 SIEM 替代能力（仅保留本项目范围内可观测与审计）。
- 全厂商零适配（先以有限设备类型打通闭环）。

## 交付标准（Definition of Done）
- 链路可跑通：防御链路与扫描链路都可完成一次端到端闭环。
- 操作可审计：关键动作均有 `trace_id`、操作者、时间、结果、证据。
- AI 可解释：评分、建议、报告能给出证据与理由。
- 风险可控：高风险动作具备审批、幂等、重试与回滚标记。
- 结果可复盘：报告、日志、任务状态可回查。

## 接口与路由规范
- API 统一前缀：`/api/`
- 接口版本建议：`/api/v1/...`
- 网关/反向代理统一转发 `/api/*` 到 Python 服务
- 统一响应结构：`code`, `message`, `data`, `trace_id`
- 统一鉴权与白名单策略：
  - 默认接口需鉴权（JWT/RBAC）
  - API 白名单仅保留必要公共接口（如登录、健康检查）
  - 白名单接口单独记录审计，避免被滥用

### 推荐接口分层
- `api/auth.py`: 登录、刷新、鉴权。
- `api/defense.py`: 告警接入、待办、审批执行。
- `api/scan.py`: 资产、任务、结果查询。
- `api/report.py`: AI 报告生成与导出。
- `api/ai_chat.py`: 多轮对话与上下文问答。
- `api/tts.py`: 语音任务提交、状态跟踪。
- `api/firewall.py`: 外部防火墙同步下发与回执。

### 建议通用错误码
- `0`: 成功。
- `400xx`: 参数与校验错误。
- `401xx`: 鉴权失败。
- `403xx`: 权限不足。
- `404xx`: 资源不存在。
- `409xx`: 状态冲突（重复执行、幂等冲突）。
- `500xx`: 系统异常。
- `502xx`: 外部依赖异常（MCP / 防火墙 API / 扫描器）。

## 需要用户确认的事项（User Review Required）
> [!IMPORTANT]
> - **外部依赖**:
>   - `python-nmap`: 需要宿主机安装 `Nmap` 工具。
>   - 交换机控制: 需要通过 Telnet/SSH 访问交换机的网络权限。
>   - 本地 LLM/TTS: 需要运行推理服务（如 `Ollama` / `LocalAI`）或可访问的 API。
> - **人工确认机制**: 防御动作需经 AI 分析后，由管理员在 Web 端确认执行（Human-in-the-loop）。
> - **外部联动前置确认**: 若启用外部防火墙 API，需确认签名方式、幂等策略、失败重试与回执字段。

## 拟定变更（Proposed Changes）
### 后端（Python / FastAPI）
目录结构：`/backend`

#### [新建] `backend/main.py`
- 程序入口，生命周期事件（数据库初始化、任务调度器初始化），CORS 配置与健康检查。

#### [新建] `backend/core/database.py`
- SQLite 连接字符串与会话管理。
- 模型定义：
  - `ThreatEvent`: 威胁事件（包含 `risk_score`、`ai_suggestion`、`status`：`PENDING` / `APPROVED` / `REJECTED`）。
  - `ScanTask`, `Asset`, `BlockLog`。
  - 扩展表：`ai_tts_task`、`plugin_registry`、`push_channel`、`firewall_sync_task`、`model_profile`。

#### [新建] `backend/api/`
- `auth.py`: JWT 登录接口、Token 刷新、RBAC 权限控制。
- `defense.py`:
  - 接收 HFish 告警。
  - 获取待处置事件列表（Pending Events）。
  - 执行处置动作（Approve/Reject）并触发交换机封禁。
- `scan.py`: 资产管理、扫描任务触发与结果查询。
- `report.py`: AI 分析生成、报告导出接口。
- `ai_chat.py`: AI 多轮对话接口（事件/任务/资产上下文）。
- `tts.py`: 本地 TTS 任务提交、状态查询、音频索引。
- `firewall.py`: 外部防火墙同步封堵（签名、幂等、重试、回执追踪）。

#### [新建] `backend/services/ai_engine.py`（核心 AI 逻辑）
- **Prompt 设计**:
  1. **风险评估 Prompt**:
     - 输入：攻击者 IP、攻击类型、攻击频率、历史行为。
     - 输出：`{"score": 85, "reason": "...", "action_suggest": "BLOCK"}`。
  2. **扫描分析 Prompt**:
     - 输入：Nmap 扫描结果（XML/JSON）。
     - 输出：Markdown 格式的风险分析与修复建议。
- **模型适配**: 封装 `LocalLLMClient`（支持 `Ollama` / `LocalAI` API）。
- **决策逻辑**:
  - `Risk Score >= 80` -> 建议 `BLOCK`（自动推送待办）。
  - `Risk Score < 80` -> 建议 `MONITOR`（持续观察）。

#### [新建] `backend/services/mcp_client.py`（MCP 客户端集成）
- **功能**: 调用现有 MCP 工具执行交换机操作。
- **通信方式**: `stdio`（子进程）或 `SSE`（HTTP）。
- **指令调用**:
  - `use_mcp_tool(server_name, tool_name="block_ip", arguments={"ip": "1.2.3.4"})`
- **执行流程**:
  1. 接收封禁任务（IP）。
  2. 构造 MCP 工具调用请求。
  3. 发送至 MCP Server。
  4. 解析 MCP 返回结果。
  5. 记录操作日志到 Database。

#### [新建] `backend/services/scanner.py`（扫描任务队列）
- **调度机制**: 通过 `asyncio.create_task` 或轻量任务队列管理长耗时扫描。
- **扫描参数**: 仅开放常用参数组合（如 `-sS -sV -p 1-65535`），避免命令注入。
- **漏洞扫描支持（NSE）**:
  - 通过 `--script` 调用 Nmap 脚本引擎。
  - 示例：`--script smb-vuln-ms17-010`、`--script vuln`。
- **结果处理**:
  1. 解析 Nmap XML 输出（`python-nmap`）。
  2. 提取 `<host>`、`<port>`、`<service>`、`<script>`（漏洞信息）。
  3. 结构化写入 `ScanResult`。
  4. 触发 AI 分析并生成修复建议。

### 前端（Vue 3 + Vite）
目录结构：`/frontend`

#### [新建] `frontend/src/router/index.ts`
- Hash 模式路由：`createWebHashHistory()`。

#### [新建] `frontend/src/views/`
1. **DefenseDashboard.vue（防御监控）**
   - **UI 组件**: `StatsCard`（今日攻击数、封禁数）、`DataTable`（实时威胁列表）、`Dialog`（封禁确认弹窗）。
   - **功能**:
     - 实时刷新 HFish 告警。
     - **待办区**: 高亮显示 `Pending Review` 事件，由 AI 给出处置建议，管理员执行 `Approve/Reject`。

2. **ScanManager.vue（资产与扫描）**
   - **UI 组件**: `AssetTable`（资产列表）、`ScanConfigModal`（扫描配置弹窗）、`VulnReportCard`（漏洞详情卡片）。
   - **可视化（Visualization）**:
     - **网络拓扑图（Topology）**: 使用 `Cytoscape.js` 或 `ECharts` 展示主机关联关系与开放端口。
     - **端口矩阵（Port Matrix）**: 使用热力图展示端口开放情况（红=高危，绿=安全）。
     - **漏洞分布（Vuln Pie Chart）**: 饼图展示高/中/低危漏洞占比。
   - **功能**: 新增扫描任务（支持勾选 Script），查看 Nmap 原始输出与 AI 解读。

3. **AICenter.vue（AI 中枢）**
   - **UI 组件**: `ChatInterface`（对话框）、`ReportGenerator`（报告配置）。
   - **AI 对话（Chat）**:
     - **上下文感知**: 自动带入当前选中的 IP 或扫描任务作为 context。
     - **示例问答**: “IP 1.2.3.4 为什么被报高危？”，“这个 Samba 漏洞怎么修？”。
     - **追问机制**: 支持多轮对话，深入分析问题。
   - **AI 报告（Report）**:
     - **日报/周报**: 自动汇总当日拦截数、高危资产数。
     - **格式**: 生成 Markdown/PDF 下载。
   - **功能**: 与 AI 对话（如“分析 IP 1.2.3.4”），生成并下载 PDF/Markdown 报告。

#### [新建] `frontend/src/components/`
- 统一集成 `shadcn-vue` 与 `ai-elements-vue` 组件体系。

### 基础设施与依赖
#### [新建] `requirements.txt`
- `fastapi`, `uvicorn`, `python-nmap`, `sqlalchemy`, `pydantic`
- 建议补充：`python-jose`, `passlib`, `httpx`, `pytest`

## 后端目录约定
- 新增统一目录：`/api/`
- 约定：后端 API 的 Python 文件统一放在 `api/` 目录下（按模块分文件）
- 示例：`api/auth.py`, `api/defense.py`, `api/scan.py`, `api/report.py`


## 简单 Mind 思维导图
```text
AimiGuard（AI安全运营平台）
├─ 一、防御监控
│  ├─ 威胁输入（hifi蜜罐 / 黑名单API）
│  ├─ SQLite临时缓存
│  ├─ AI风险评分与策略建议
│  ├─ 自动控制交换机封禁（MCP + tele）
│  └─ 处置结果回传与审计
├─ 二、探测扫描（主动）
│  ├─ 目标资产管理（IP/网段/主机）
│  ├─ 调用 Kali / MCP / 漏洞工具
│  ├─ 端口与服务识别 / 漏洞检测
│  ├─ 扫描结果写入SQLite
│  └─ AI生成风险报告与修复建议
└─ 三、AI智能中枢
   ├─ AI对话（问答、追问、解释）
   ├─ AI分析（关联、聚类、异常检测）
   └─ AI报告（日报/周报/专项报告）
```

## 核心原理（基础版）
1. 防御监控与探测扫描的数据统一进入 `SQLite` 临时缓存。
2. AI 中枢对事件与扫描结果进行风险评分、关联分析与优先级排序。
3. 防御链路通过策略引擎决策后，调用 MCP tools 执行封禁与回滚。
4. 探测链路通过任务编排调用 Kali/MCP/漏洞工具主动扫描目标。
5. Web 面板提供 AI 对话、AI 分析看板、AI 报告中心和全链路审计。

## 主流程（如图）
### A. 防御监控流程
1. `hifi 蜜罐` 与 `黑名单数据 API` 产生可疑 IP。
2. 数据标准化后写入 `SQLite` 临时缓存。
3. AI 输出风险评分、动作建议与理由。
4. Python 执行器从 `SQLite` 拉取处置队列。
5. 调用自研 `MCP tools` 经 `tele` 端口控制多个交换机。
6. 按逻辑顺序执行封禁（支持失败重试与回滚标记）。
7. Web 展示执行状态、AI 分析与处置报告。

### B. 探测扫描流程（主动）
1. 配置扫描目标（单 IP、网段、资产组）。
2. 任务编排器调用 Kali/MCP/漏洞工具执行扫描。
3. 采集端口、服务、漏洞、弱口令等结果并写入 `SQLite`。
4. AI 对扫描结果做风险分级、漏洞关联与修复建议。
5. 输出扫描报告（摘要版 + 详细版），支持导出与审计存档。

## 模块拆分（子内容）
### 1) 防御监控模块
- `collector`
  - 对接黑名单 API、蜜罐数据
  - 字段校验、去重、重复来源合并
- `normalizer`
  - 统一数据结构与风险等级
  - 写入 `SQLite` 临时缓存并维护状态字段
- `policy-engine`
  - 规则决策（封禁/观察/忽略）
  - AI 风险评分、策略建议、白名单保护、阈值控制、审批条件
- `executor`
  - 任务编排、队列执行、重试机制
  - 幂等处理（同一 IP 避免重复封禁）
- `mcp-tools`
  - 多交换机驱动适配
  - 命令模板与厂商差异屏蔽

### 2) 探测扫描模块（主动）
- `asset-manager`
  - 管理扫描目标（IP/网段/资产组）
  - 目标标签、优先级、扫描窗口控制
- `scan-orchestrator`
  - 编排 Kali/MCP/漏洞工具扫描任务
  - 控制并发、超时、重试与任务隔离
- `vuln-adapter`
  - 统一不同扫描工具输出格式
  - 漏洞去重、CVE 映射、严重级别归一
- `scan-result-center`
  - 扫描结果写入 `SQLite`
  - 形成资产维度风险画像与历史趋势

### 3) AI 与前端模块
- `web-console`
  - 基于 `Vue` 开发（前后端分离 + Hash 路由）
  - 组件统一使用 `ai-elements-vue` 与 `shadcn-vue`
  - 实时状态、任务详情、执行日志
  - 审批入口、手动回滚、报表导出
- `ai-copilot`
  - AI 对话：问答、追问、上下文解释
  - AI 分析：关联分析、告警聚类、异常检测
  - AI 报告：摘要版/详细版报告、日报/周报/专项报告
  - 语音 TTS：本地模型语音播报告警与摘要
- `plugin-hub`
  - MCP 第三方插件接入（如 bot）
  - 异常推送通道管理（Webhook/机器人/IM）
- `firewall-connector`
  - 对接外部防火墙 API
  - 将封禁 IP 同步下发到防火墙（支持回执与失败重试）

## AI 强化重点（本期）
- `AI-risk`：对每条威胁事件与扫描发现输出风险分（0-100）与处置优先级。
- `AI-decision`：给出动作建议（封禁/观察/忽略/立即修复）并提供可读理由。
- `AI-explain`：对执行结果给出解释（成功原因、失败根因、修复建议）。
- `AI-cluster`：对相似告警和漏洞结果聚类，降低告警噪音与重复处置。
- `AI-chat`：支持基于当前任务上下文的多轮对话（问原因、问影响、问下一步）。
- `AI-report`：自动生成班次总结、日报、周报、专项漏洞分析报告，支持导出。
- `AI-tts`：支持本地大模型 TTS 语音播报（告警、结论、摘要）。
- `AI-model-router`：主模型默认本地部署，支持按策略切换不同模型。

## 模型与推理策略（本地优先）
- 主语言模型：本地大模型（默认）
- 模型切换：支持按任务类型切换（对话/分析/报告/语音）
- 路由策略：可按延迟、成本、准确率、可用性自动选择模型
- TTS 策略：语音播报默认本地 TTS 模型，支持替换语音引擎
- 合规策略：敏感数据默认本地处理，外发需显式开关与审计

## 外部防火墙 API 对接（未来能力）
- 目标：将高风险 IP 在处置后同步到外部防火墙 API 做二次封堵
- 下发流程：策略确认 -> 生成防火墙动作 -> API 下发 -> 回执记录 -> 失败重试
- 对接方式：标准 REST API / 厂商 SDK 适配层
- 安全要求：接口签名、TLS、IP 白名单、请求幂等键、重放保护
- 审计要求：记录目标防火墙、策略ID、请求体摘要、回执码、trace_id
## AI 对话与 AI 分析报告（详细）
- AI 对话内容
  - 可按事件/任务/资产发起对话：例如“这个 IP 为什么被封禁？”
  - 支持追问：例如“如果不封禁，影响范围是什么？”
  - 支持语音播报结果（本地 TTS）
  - 对话内容与引用证据（日志/告警/扫描结果）关联存档
- AI 分析内容
  - 防御监控：攻击来源画像、重复攻击路径、封禁效果评估
  - 探测扫描：高危漏洞链路、横向风险扩散路径、修复优先级建议
  - 统一输出：风险等级、置信度、证据列表、建议动作
- AI 报告内容
  - 摘要版：关键风险、处置动作、未闭环项
  - 详细版：资产维度、漏洞维度、事件维度、时间线
  - 管理版：趋势统计、处置 SLA、误报率、修复进度
- 报告导出
  - 支持按时间范围/资产组导出
  - 支持归档并关联审计记录

## 报告模板建议（可直接落地）
- 防御监控报告
  - 概览：事件总数、高危占比、处置成功率、平均响应时间
  - 详情：Top 攻击源 IP、封禁动作明细、失败原因与回滚记录
  - 建议：白名单调整、策略阈值优化、设备侧加固项
- 探测扫描报告
  - 概览：扫描资产数、发现漏洞数、高危漏洞数、未修复项
  - 详情：资产-端口-服务-漏洞清单、证据截图/日志引用
  - 建议：修复优先级（P0/P1/P2）、复测计划、责任人建议

## AI 对话示例（面板内）
- 问：`这个 IP 为什么被封禁？`
- 答：`AI 根据近 30 分钟攻击频次、命中规则、历史行为相似度给出高风险结论，建议封禁 24 小时。`
- 问：`这个漏洞需要立即修复吗？`
- 答：`该漏洞 CVSS 高，且服务暴露在公网，建议 24 小时内修复并进行复测。`
- 问：`本周风险变化趋势如何？`
- 答：`高危事件环比下降 12%，但弱口令相关告警上升 18%，建议强化口令策略。`

## 交换机密码等保存（详细）
建议实现 `credential-vault` 子模块，要求如下：
- 存储内容
  - 设备地址、端口、用户名、密码/密钥、设备类型、标签
- 安全策略
  - 密码在库中必须加密保存（如 AES-GCM）
  - 加密主密钥来自环境变量或外部密钥服务，不写入代码仓库
  - 展示层不返回明文密码，仅返回掩码和更新时间
- 使用策略
  - 执行时临时解密到内存，用后立即释放
  - 记录谁在什么时间使用了哪台设备凭据
- 权限策略
  - 凭据读取与编辑分离权限（最小权限原则）
  - 关键修改需二次确认

## 面板保护（详细）
`web-console` 需要最小安全基线：
- 身份认证
  - 登录态管理（JWT + 过期时间 + 刷新机制）
  - 支持 2FA（MVP 可先预留接口）
- 访问控制
  - RBAC 角色：`viewer`、`operator`、`admin`
  - 高风险动作（批量封禁/回滚）仅 `operator/admin`
- 安全防护
  - 全站 HTTPS
  - CSRF 防护、接口限流、防暴力登录
  - 登录失败告警和 IP 限制策略
- 审计与告警
  - 审计日志不可篡改（追加写）
  - 风险操作（批量封禁、凭据更新）触发通知

## 数据模型建议（MVP）
- `threat_event`: `id`, `ip`, `source`, `risk_level`, `ai_score`, `ai_reason`, `timestamp`, `status`
- `execution_task`: `id`, `event_id`, `device_id`, `action`, `state`, `retry_count`, `started_at`, `ended_at`
- `scan_task`: `id`, `target`, `target_type`, `tool_name`, `state`, `started_at`, `ended_at`
- `scan_finding`: `id`, `scan_task_id`, `asset`, `port`, `service`, `vuln_id`, `severity`, `evidence`, `status`
- `device`: `id`, `name`, `ip`, `port`, `vendor`, `enabled`
- `credential`: `id`, `device_id`, `username`, `secret_ciphertext`, `key_version`, `updated_at`
- `ai_decision_log`: `id`, `event_id`, `model_name`, `decision`, `confidence`, `reason`, `created_at`
- `ai_chat_session`: `id`, `context_type`, `context_id`, `operator`, `started_at`
- `ai_chat_message`: `id`, `session_id`, `role`, `content`, `evidence_refs`, `created_at`
- `ai_report`: `id`, `report_type`, `scope`, `summary`, `detail_path`, `created_at`
- `ai_tts_task`: `id`, `source_type`, `source_id`, `voice_model`, `audio_path`, `state`, `created_at`
- `plugin_registry`: `id`, `plugin_name`, `plugin_type`, `endpoint`, `enabled`, `updated_at`
- `push_channel`: `id`, `channel_type`, `target`, `enabled`, `updated_at`
- `firewall_sync_task`: `id`, `ip`, `firewall_vendor`, `policy_id`, `request_hash`, `state`, `retry_count`, `created_at`
- `model_profile`: `id`, `model_name`, `model_type`, `is_local`, `priority`, `enabled`
- `audit_log`: `id`, `operator`, `module`, `action`, `result`, `created_at`, `trace_id`

## 验证计划（Verification Plan）
### 自动化测试
- **后端测试**: 使用 `pytest` 测试 API 端点和业务逻辑（Mock Nmap 和交换机连接）。
- **前端测试**: 组件渲染测试、路由跳转测试、关键交互状态测试（审批按钮与任务状态联动）。

### 人工验证
1. **防御流程（Human-in-the-loop）**:
   - 模拟 HFish 告警 -> 写入 SQLite。
   - 触发 AI 分析 -> 生成评分和建议 -> 状态置为 `PENDING`。
   - **Web 端显示待办事项** -> 用户点击“封禁/驳回” -> API 更新状态 -> 触发交换机封禁命令或归档驳回。
2. **扫描流程**:
   - 添加 localhost 资产 -> 触发扫描 -> 检查 Nmap 解析结果 -> 验证 AI 报告生成。
   - 勾选 NSE Script 扫描 -> 验证漏洞脚本输出可解析并进入漏洞视图。
3. **UI 验证**:
   - 检查 Hash 路由导航和组件样式是否统一。
   - 检查 DefenseDashboard / ScanManager / AICenter 页面数据刷新与交互反馈是否符合预期。
4. **联动验证**:
   - 验证 MCP 调用日志、失败重试、幂等去重与最终状态一致性。
   - 验证外部防火墙 API 回执记录、失败重试、审计字段完整性。

## 第一版里程碑
- [ ] 打通防御监控链路：API/蜜罐 -> SQLite -> Python 执行 -> 交换机封禁
- [ ] 打通探测扫描链路：资产配置 -> Kali/MCP/漏洞工具 -> SQLite 入库
- [ ] 完成 1 台交换机封禁闭环 + 1 套扫描工具闭环
- [ ] 完成统一 `/api/` 路由规范与 `/api/v1` 版本化
- [ ] 完成前后端分离部署与前端 Hash 路由
- [ ] 完成 API 白名单与鉴权策略落地
- [ ] 完成 `api/` 目录改造（后端 API Python 文件归一）
- [ ] 扩展到多台交换机并按顺序执行
- [ ] 增加凭据加密存储与读取审计
- [ ] 增加面板登录、RBAC、高风险操作确认
- [ ] 上线 AI 对话（基于任务上下文）
- [ ] 上线 AI 分析（聚类、解释、修复建议）
- [ ] 上线 AI 报告中心（日报/周报/专项报告）
- [ ] 上线本地模型 TTS 语音播报（告警与报告摘要）
- [ ] 接入 MCP 第三方插件（如 bot）与异常推送通道
- [ ] 增加外部防火墙 API 同步封堵（含回执、重试、审计）
- [ ] 实现本地模型默认 + 可切换模型路由

## 实施建议
- 先做 MVP：`Python + SQLite + Vue` 固定架构，完成防御监控闭环 + 探测扫描闭环 + 最小审批流程
- 再做增强：多厂商设备适配、更多扫描插件、规则可视化配置、联动告警
- AI 持续优化：决策可解释性、报告质量、误报率、修复建议命中率
- 模型策略：本地模型优先，外部模型按策略切换并保留审计
- 持续优化：执行耗时、告警噪音、审计完整性与可追溯性

## 备注
- `SQLite` 作为临时中间缓存，建议字段覆盖事件、任务、扫描结果、AI 结论、对话与报告索引。
- 封禁与扫描动作必须保留审计日志：操作者、目标、命令/工具、结果、时间、追踪ID。
- API 统一使用 `/api/` 前缀，前端使用 Hash 路由，保持前后端分离架构一致性。
- API 白名单仅允许必要公共接口，其他接口默认鉴权。
- 后端 API Python 文件统一放在 `api/` 目录。
- 默认使用本地语言模型与本地 TTS，模型切换需可配置并记录审计。
- 支持 MCP 第三方插件与异常推送通道，插件调用需做权限控制。
- 外部防火墙 API 联动封堵需支持签名、幂等、重试和回执追踪。
- 组件规范：前端组件库统一使用 `https://www.ai-elements-vue.com/` 与 `https://www.shadcn-vue.com/`。

## 建议目录结构（目标）
```text
backend/
  main.py
  core/
    database.py
  api/
    auth.py
    defense.py
    scan.py
    report.py
    ai_chat.py
    tts.py
    firewall.py
  services/
    ai_engine.py
    mcp_client.py
    scanner.py
frontend/
  src/
    router/
      index.ts
    views/
      DefenseDashboard.vue
      ScanManager.vue
      AICenter.vue
    components/
requirements.txt
```

## 配置与环境变量建议
- `APP_ENV`: `dev` / `test` / `prod`。
- `DATABASE_URL`: 默认 `sqlite:///aimiguard.db`。
- `JWT_SECRET`: JWT 签名密钥。
- `JWT_EXPIRE_MINUTES`: Token 过期时长。
- `LLM_PROVIDER`: `ollama` / `localai` / `custom`。
- `LLM_BASE_URL`: 本地模型服务地址。
- `TTS_PROVIDER`: 本地 TTS 引擎类型。
- `MCP_MODE`: `stdio` / `sse`。
- `MCP_SERVER_NAME`: MCP 服务标识。
- `FIREWALL_API_URL`: 外部防火墙 API 地址。
- `FIREWALL_API_KEY`: 外部防火墙鉴权密钥。
- `AUDIT_ENABLED`: 审计开关。

## 运维与运行手册（Runbook）
### 日常巡检
- 检查待办队列堆积量（`PENDING` 数量与平均停留时长）。
- 检查扫描任务失败率、平均耗时、重试次数。
- 检查 MCP 调用失败原因分布（网络、认证、设备不可达）。
- 检查外部防火墙同步回执成功率。

### 故障处置
1. 封禁执行失败：
   - 先确认设备网络连通与凭据有效性。
   - 再检查 MCP 工具返回码与错误信息。
   - 按重试策略执行，必要时转人工处理并记录原因。
2. 扫描任务超时：
   - 检查目标可达性与扫描参数。
   - 降低并发、缩小端口范围重试。
3. AI 服务不可用：
   - 切换到备用模型配置。
   - 保留人工决策路径，避免阻断主流程。

## 安全与合规基线
- 全站 HTTPS、接口签名、最小权限、敏感配置不入库。
- 凭据加密保存（如 AES-GCM），主密钥来自环境变量或外部 KMS。
- 审计日志追加写，禁止篡改，关键动作需要二次确认。
- 高风险动作默认人工审批，支持回滚标记与复核。

## 性能与容量规划（建议）
- 数据生命周期：事件/任务按周期归档，避免 SQLite 长期膨胀。
- 队列控制：限制并发与队列深度，防止扫描风暴。
- 指标监控：任务吞吐、失败率、平均响应、外部依赖可用性。
- 告警策略：按严重级别分层通知，降低噪声。

## 后续演进路线
- 多厂商交换机适配层扩展。
- 漏洞工具适配器扩展（统一结果协议）。
- 策略引擎可视化配置。
- 报告模板中心化与分角色输出。
- 审计看板与合规报表自动化。

