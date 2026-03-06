# 对比记录 & TODO 列表

> **参考来源**：`资料/ai_lzx_v2-0306`（已跑通的功能实现）vs 主项目 `frontend`（Vue 3 + Vite SPA）
>
> **目标**：将参考实现中已跑通的功能完整移植/补全到主项目中。

---

## 一、整体架构对比

| 维度 | ai_lzx_v2-0306（参考实现） | 主项目 frontend |
|------|--------------------------|-----------------|
| 前端架构 | 多页 MPA + Flask Jinja2 模板 + Vue 3 CDN | 单页 SPA + Vite + Vue 3 + TypeScript |
| UI 框架 | Vuetify 3 | 自定义 UI（radix-vue + Tailwind CSS） |
| 数据请求 | 原生 `fetch()` 直连本地 API | axios + `/api/v1` + JWT Bearer Token |
| 状态管理 | 组件内 `ref/reactive` | Pinia + composables |
| 图表 | Chart.js（CDN） | 暂无图表库（缺失！） |
| 认证 | 无认证 | JWT Token + 角色控制（admin/operator/viewer） |
| 路由 | Flask 路由 | Vue Router 4（前端路由） |
| 后端 | Flask（Python） | 独立后端（通过 `/api/v1` 接入） |

---

## 二、功能模块对比

### 2.1 HFish 蜜罐集成

| 功能点 | 参考实现（已跑通） | 主项目 frontend | 状态 |
|--------|-------------------|-----------------|------|
| HFish 配置页面（地址/密钥/间隔/启用） | ✅ `vuetify_settings.html` | ✅ `IntegrationsPage.vue` | **已有** |
| 手动触发同步按钮 | ✅ | ✅ `defenseApi.triggerHFishSync()` | **已有** |
| 攻击日志列表页面 | ✅ `vuetify_hfish.html`（独立页面） | ⚠️ 仅 `DefenseRealtime.vue` 有实时流，无完整攻击日志页 | **缺失** |
| 攻击日志：分页展示 | ✅ | ❌ | **缺失** |
| 攻击日志：按威胁等级筛选 | ✅ | ❌ | **缺失** |
| 攻击日志：按服务名筛选 | ✅ | ❌ | **缺失** |
| 攻击日志：点击 IP 联动 Nmap 详情弹窗 | ✅ | ⚠️ `DefenseDashboard.vue` 有 IP→Nmap 弹窗，但依赖后端接口 | **部分** |
| 威胁统计（按等级/服务/IP） | ✅ `GET /api/hfish/stats` | ❌ 主项目没有此数据视图 | **缺失** |
| 近 7 天攻击趋势折线图 | ✅ Chart.js 实现 | ❌ 无图表库，无此视图 | **缺失** |
| TOP 10 攻击来源 IP 排行 | ✅ | ❌ | **缺失** |
| TOP 10 被攻击服务统计 | ✅ | ❌ | **缺失** |

---

### 2.2 Nmap 网络扫描

| 功能点 | 参考实现（已跑通） | 主项目 frontend | 状态 |
|--------|-------------------|-----------------|------|
| Nmap 配置（IP 范围/参数/间隔/启用） | ✅ `vuetify_settings.html` | ✅ `IntegrationsPage.vue`（`scanApi.saveNmapConfig`） | **已有** |
| 手动触发 Nmap 扫描 | ✅ `POST /api/nmap/scan` | ✅ `scanApi.triggerNmapScan()` | **已有** |
| 扫描历史列表（下拉选择） | ✅ `vuetify_nmap.html` | ❌ `ScanManager.vue` 只有任务列表，无扫描历史 | **缺失** |
| 主机列表（按扫描选择） | ✅ | ❌ | **缺失** |
| 主机详情弹窗（OS/MAC/端口/服务） | ✅ | ❌ ScanManager 只有发现项，无主机详情视图 | **缺失** |
| 资产追踪（按 MAC，含 IP 历史） | ✅ `GET /api/nmap/assets` + `/ips` | ❌ 主项目 Asset 概念是管理扫描目标，不是 Nmap 发现的设备 | **缺失** |
| 主机状态统计（up/down 分布） | ✅ `GET /api/nmap/stats` | ❌ | **缺失** |
| 厂商分布统计 | ✅ | ❌ | **缺失** |
| OS 标签自动识别 | ✅ `auto_detect_os_tags()` | ✅（后端逻辑，`getWin7Hosts` 有使用） | **已有（后端）** |

---

### 2.3 漏洞扫描

| 功能点 | 参考实现（已跑通） | 主项目 frontend | 状态 |
|--------|-------------------|-----------------|------|
| 漏洞扫描结果列表 | ✅ `vuetify_vuln.html` | ✅ `ScanManager.vue` 漏洞发现 Tab | **已有** |
| 漏洞结果按严重等级筛选 | ✅ | ✅ | **已有** |
| 漏洞结果状态更新 | ❌（无此功能） | ✅ `scanApi.updateFindingStatus()` | **主项目更好** |
| 手动触发漏洞扫描 | ✅ `POST /api/nmap/vuln/scan` | ❌（无此按钮） | **缺失** |
| 漏洞统计（vulnerable/safe/error 计数） | ✅ `GET /api/nmap/vuln/stats` | ❌（无此视图） | **缺失** |
| 受影响设备数（按 MAC 去重） | ✅ | ❌ | **缺失** |
| 漏洞脚本规则可视化配置 | ✅ 按标签配置漏洞脚本 | ❌ | **缺失** |
| 扫描 Profile 配置 | ❌ | ✅ `scanApi.getProfiles()` | **主项目已有** |

---

### 2.4 仪表盘总览

| 功能点 | 参考实现（已跑通） | 主项目 frontend | 状态 |
|--------|-------------------|-----------------|------|
| 综合统计卡片（攻击/主机/漏洞） | ✅ `vuetify_index.html` | ✅ `OverviewPage.vue`（有 KPI 卡片） | **已有** |
| 攻击趋势图（折线图） | ✅ Chart.js | ⚠️ 无图表库，OverviewPage 有数据无图表 | **缺图表** |
| 威胁分布饼图 | ✅ | ❌ | **缺失** |
| TOP 攻击 IP 排行 | ✅ | ✅ `OverviewPage.vue` 有 TOP 攻击 IP | **已有** |
| 探测侧仪表盘（扫描任务/资产/漏洞） | ❌（无此概念） | ✅ `ProbeDashboardPage.vue` | **主项目独有** |

---

### 2.5 系统设置与配置

| 功能点 | 参考实现（已跑通） | 主项目 frontend | 状态 |
|--------|-------------------|-----------------|------|
| HFish 配置 | ✅ | ✅ IntegrationsPage | **已有** |
| Nmap 配置 | ✅ | ✅ IntegrationsPage | **已有** |
| 漏洞脚本规则编辑（可视化+JSON） | ✅ | ❌ | **缺失** |
| API 密钥脱敏保护（GET 不返回，POST 留空保留） | ✅ | ✅（后端逻辑） | **已有** |
| 防御模式/主动探测模式切换 | ❌ | ✅ `SettingsPage.vue` + `Layout.vue` 切换动画 | **主项目独有** |
| 推送通道配置（Webhook/企微/钉钉/邮件） | ❌ | ✅ `IntegrationsPage.vue` | **主项目独有** |

---

### 2.6 其他功能

| 功能点 | 参考实现 | 主项目 frontend | 状态 |
|--------|----------|-----------------|------|
| 用户认证（登录/登出/JWT） | ❌ 无认证 | ✅ `Login.vue` + `authApi` + 路由守卫 | **主项目独有** |
| 角色权限控制（admin/operator/viewer） | ❌ | ✅ | **主项目独有** |
| AI 研判/分析（对话+报告） | ❌ | ✅ `AICenter.vue` + `aiApi` + TTS | **主项目独有** |
| 审计日志 | ❌ | ✅ `AuditPage.vue` | **主项目独有** |
| 系统可观测性（指标/告警/延迟） | ❌ | ✅ `ObservabilityPage.vue` | **主项目独有** |
| 威胁事件审批/驳回流程 | ❌ | ✅ `DefenseDashboard.vue` | **主项目独有** |
| 实时数据轮询（15s 间隔） | ❌（页面刷新） | ✅ 两个 Realtime 页面 | **主项目独有** |
| 粒子背景动画效果 | ❌ | ✅ `ParticleBackground.vue` | **主项目独有** |
| 防御/探测模式切换 GSAP 动画 | ❌ | ✅ `Layout.vue` | **主项目独有** |

---

## 三、主项目缺少的内容（需要补充）

> 以下是 `参考实现` 中已跑通、但 `主项目 frontend` 中**缺失或不完整**的功能，按优先级排序。

---

### 🔴 高优先级（核心功能缺失）

#### P1-1. 攻击日志完整页面

**参考**：`vuetify_hfish.html`  
**缺失**：主项目无独立的攻击日志列表页，只有 DefenseRealtime 的实时流视图  
**需要新增**：
- 完整的攻击日志分页列表视图（在 `DefenseDashboard.vue` 或新建页面）
- 按威胁等级快速筛选
- 按服务名筛选
- 时间范围筛选
- 点击 IP 联动弹出 Nmap 主机详情弹窗

**API 对接**：
- `GET /api/v1/defense/hfish/logs?limit=&offset=&threat_level=&service_name=`（需后端新增）
- 或直接复用现有 `GET /api/v1/defense/events`，确认字段覆盖

---

#### P1-2. 攻击统计图表（图表库引入）

**参考**：`vuetify_index.html` Chart.js 实现  
**缺失**：主项目无图表库（package.json 中未引入），`OverviewPage.vue` 有趋势数据但无图表  
**需要新增**：
- 引入图表库（推荐 `chart.js + vue-chartjs` 或 `echarts`）
- 防御仪表盘：攻击趋势折线图（近7天）
- 防御仪表盘：威胁等级分布饼图
- 防御仪表盘：TOP 10 攻击服务柱状图

---

#### P1-3. Nmap 主机扫描结果视图

**参考**：`vuetify_nmap.html`  
**缺失**：主项目 ScanManager 只有资产管理（待扫描目标）和漏洞发现，没有 Nmap 扫描后的主机列表结果视图  
**需要新增**：
- 扫描历史选择器（选择不同时间的扫描批次）
- 主机列表：IP / MAC / 厂商 / OS / 状态 / 开放端口数
- 主机详情弹窗：OS 信息 / 端口列表 / 服务版本
- 主机在线/离线状态统计

**API 对接**（需后端确认/新增）：
- `GET /api/v1/scan/nmap/hosts?scan_id=&state=`
- `GET /api/v1/scan/nmap/scans`
- `GET /api/v1/scan/nmap/host/<ip>`

---

#### P1-4. 资产追踪视图（按 MAC 去重，含 IP 历史）

**参考**：`GET /api/nmap/assets` + `/api/nmap/assets/<id>/ips`  
**缺失**：主项目的 `Asset` 概念是"待扫描目标"（手动添加的 IP/CIDR），不是 Nmap 自动发现的设备  
**需要新增**（或区分）：
- "已发现资产"列表视图（Nmap 自动发现的设备，按 MAC 去重）
- 资产 IP 历史追踪（同一设备 IP 变化记录）
- 与手动管理的"扫描资产"做区分

---

### 🟠 中优先级（功能增强）

#### P2-1. 漏洞扫描统计卡片

**参考**：`vuetify_vuln.html` + `GET /api/nmap/vuln/stats`  
**缺失**：`ScanManager.vue` 漏洞发现 Tab 没有统计卡片  
**需要新增**：
- 漏洞数量统计卡片：总计 / 存在漏洞 / 已确认安全 / 扫描失败 / 受影响设备数

---

#### P2-2. 手动触发漏洞扫描按钮

**参考**：`POST /api/nmap/vuln/scan`  
**缺失**：ScanManager.vue 漏洞 Tab 无手动触发漏洞扫描的入口  
**需要新增**：
- 漏洞 Tab 顶部增加"立即漏洞扫描"按钮（参考创建任务按钮）
- 对接 `POST /api/v1/scan/nmap/vuln/scan`（需后端确认接口）

---

#### P2-3. 漏洞脚本规则可视化配置

**参考**：`vuetify_settings.html` 漏洞规则编辑  
**缺失**：IntegrationsPage.vue Nmap 配置区没有漏洞脚本规则编辑  
**需要新增**：
- Nmap 配置区增加"漏洞检测规则"子区块
- 按系统标签分组展示（linux/win7/win10 等）
- 每组可增删漏洞脚本名称
- 支持高级 JSON 编辑模式（折叠展开）

**API 对接**：需在 `POST /api/v1/scan/nmap/config` 的 payload 中增加 `vuln_scripts_by_tag` 字段

---

#### P2-4. HFish 攻击统计数据接口对接

**参考**：`GET /api/hfish/stats`（返回按等级/服务/IP/趋势的统计数据）  
**缺失**：主项目前端有 `overviewApi.getDefenseStats()`，但不确认返回字段是否包含此数据  
**需要确认**：
- 后端 `GET /api/v1/overview/defense-stats` 返回字段结构
- 是否包含：threat_stats（按等级）/ service_stats（按服务）/ ip_stats（TOP IP）/ time_stats（趋势）
- 若无，需后端补充并在前端 OverviewPage.vue 中对接

---

#### P2-5. 探测仪表盘图表完善

**参考**：`vuetify_index.html` 漏洞分布图  
**缺失**：`ProbeDashboardPage.vue` 有"漏洞分布"区域但无图表（缺图表库）  
**需要新增**：
- 引入图表库后补充探测仪表盘图表
- 漏洞严重等级分布饼图
- 扫描任务状态分布饼图
- 近期任务完成趋势折线图

---

### 🟡 低优先级（体验优化）

#### P3-1. IntegrationsPage 推送通道测试功能完善

**现状**：IntegrationsPage.vue 有推送通道配置（Webhook/企微/钉钉/邮件），参考实现无此功能  
**优化点**：
- 确认测试推送按钮的后端接口 `POST /api/v1/push/channels/:id/test` 是否已实现
- 测试结果反馈 UI 优化

---

#### P3-2. 攻击日志页与 Nmap 页联动体验优化

**参考**：`vuetify_hfish.html` 点击 IP → 弹窗展示 Nmap 主机详情  
**现状**：`DefenseDashboard.vue` 已有点击 IP 查 Nmap 的逻辑，但依赖后端  
**优化点**：
- 确认后端 `GET /api/v1/scan/nmap/host/<ip>` 接口是否已实现
- 统一 IP 联动弹窗组件（复用在攻击日志、实时检测、威胁处置等多个页面）

---

#### P3-3. 数据刷新机制统一

**参考实现**：用户手动刷新页面  
**主项目**：DefenseRealtime / ProbeRealtime 已有 15s 轮询  
**优化点**：
- 攻击日志页、Nmap 主机页、漏洞结果页也应有轮询/手动刷新机制
- 同步按钮触发后自动刷新列表

---

## 四、后端 API 缺口分析

> 以下是参考实现已有、但主项目后端可能缺失的 API，需要后端同学确认或补充。

| 参考实现 API | 主项目对应 API | 状态 |
|-------------|---------------|------|
| `GET /api/hfish/logs?limit&offset&threat_level&service_name` | `GET /api/v1/defense/events`（字段不完全一致） | **需确认/补充** |
| `GET /api/hfish/stats`（按等级/服务/IP/趋势分别统计） | `GET /api/v1/overview/defense-stats` | **需确认字段** |
| `GET /api/nmap/hosts?scan_id&state` | ❌ 主项目无此接口 | **需新增** |
| `GET /api/nmap/scans`（扫描历史列表） | ❌ 主项目无此接口 | **需新增** |
| `GET /api/nmap/stats`（状态/厂商统计） | ❌ 主项目无此接口 | **需新增** |
| `GET /api/nmap/host/<ip>` | ❌ 可能已有但未确认 | **需确认** |
| `GET /api/nmap/assets?mac&ip` | ❌ 主项目 `/scan/assets` 是手动管理目标 | **需新增（Nmap发现资产）** |
| `GET /api/nmap/assets/<id>/ips` | ❌ | **需新增** |
| `GET /api/nmap/vuln/stats` | ❌ 主项目无此汇总接口 | **需新增** |
| `POST /api/nmap/vuln/scan` | ❌ 主项目无手动触发漏洞扫描接口 | **需新增** |
| `GET /api/settings`（含漏洞脚本规则） | `GET /api/v1/scan/nmap/config`（字段不同） | **需扩充字段** |

---

## 五、TODO 列表（按优先级）

### 🔴 P1 — 立即处理

- [ ] **P1-1** 引入图表库（推荐 `echarts` 或 `chart.js + vue-chartjs`），在 `package.json` 添加依赖
- [ ] **P1-2** `OverviewPage.vue`：攻击趋势折线图（近7天，调用 `overviewApi.getTrends`）
- [ ] **P1-3** `OverviewPage.vue`：威胁等级分布饼图（高/中/低）
- [ ] **P1-4** `OverviewPage.vue`：TOP 10 攻击服务柱状图
- [ ] **P1-5** 新增或完善攻击日志页（在 `DefenseDashboard.vue` 增加攻击日志 Tab，或新建 `AttackLogsPage.vue`）
  - 分页列表（limit/offset）
  - 按威胁等级筛选（高危/中危/低危）
  - 按服务名筛选
  - 时间倒序排列
- [ ] **P1-6** 后端：确认并补充 `GET /api/v1/defense/hfish/logs` 接口（分页+过滤参数）
- [ ] **P1-7** 前端 `src/api/defense.ts`：新增 `getHFishLogs(params)` 方法

### 🟠 P2 — 本周完成

- [ ] **P2-1** `ScanManager.vue` 增加"Nmap 主机"Tab
  - 扫描历史列表（下拉选择 scan_id）
  - 主机列表（IP / MAC / 厂商 / OS 标签 / 状态 / 端口数）
  - 点击主机弹窗：OS 信息 / 端口列表 / 服务版本
- [ ] **P2-2** 后端：新增 `GET /api/v1/scan/nmap/hosts` 接口（scan_id/state 过滤）
- [ ] **P2-3** 后端：新增 `GET /api/v1/scan/nmap/scans` 接口（扫描历史列表）
- [ ] **P2-4** 后端：新增 `GET /api/v1/scan/nmap/host/<ip>` 接口（单主机详情）
- [ ] **P2-5** `ScanManager.vue` 漏洞 Tab：增加统计卡片（总计/存在漏洞/安全/受影响设备）
- [ ] **P2-6** `ScanManager.vue` 漏洞 Tab：增加"立即漏洞扫描"按钮
- [ ] **P2-7** 后端：确认/新增 `GET /api/v1/scan/nmap/vuln/stats` 接口
- [ ] **P2-8** 后端：确认/新增 `POST /api/v1/scan/nmap/vuln/scan` 接口（手动触发漏洞扫描）
- [ ] **P2-9** `IntegrationsPage.vue` Nmap 配置区：增加漏洞脚本规则可视化编辑
  - 按 OS 标签分组（linux/win7/win10 等）
  - 每组可增删漏洞脚本
  - 支持 JSON 高级编辑
- [ ] **P2-10** 后端：`POST /api/v1/scan/nmap/config` 增加 `vuln_scripts_by_tag` 字段支持
- [ ] **P2-11** `ProbeDashboardPage.vue`：引入图表库后补充探测仪表盘图表（漏洞分布饼图、任务状态分布）
- [ ] **P2-12** 后端：新增 `GET /api/v1/scan/nmap/assets`（Nmap 自动发现资产列表，区别于手动管理资产）
- [ ] **P2-13** 后端：新增 `GET /api/v1/scan/nmap/assets/<id>/ips`（资产 IP 历史记录）

### 🟡 P3 — 有空再做

- [ ] **P3-1** 统一 IP 联动弹窗组件（提取为 `NmapHostDetail.vue`），在攻击日志、实时检测、威胁处置等页面复用
- [ ] **P3-2** 各数据列表页增加手动刷新按钮 + 自动轮询配置
- [ ] **P3-3** 攻击日志页：增加导出功能（CSV/JSON）
- [ ] **P3-4** `OverviewPage.vue`：接口数据确认（`overviewApi.getDefenseStats` 字段对齐）
- [ ] **P3-5** 确认 `POST /api/v1/push/channels/:id/test` 后端是否已实现，完善测试推送 UI 反馈

---

## 六、参考实现可直接复用的逻辑

| 逻辑模块 | 所在文件 | 可复用方式 |
|----------|----------|------------|
| HFish 日志增量同步逻辑 | `hfish/attack_log_sync.py` | 后端直接使用 |
| Nmap 扫描 + 解析 + 资产 upsert | `nmap/network_scan.py` | 后端直接使用 |
| OS 标签自动识别算法 | `network_scan.auto_detect_os_tags()` | 后端直接使用 |
| 漏洞扫描智能跳过逻辑 | `network_scan.should_skip_vuln()` | 后端直接使用 |
| 攻击统计 SQL 查询 | `web_app.get_hfish_stats()` | 后端参考实现 |
| Nmap 主机列表 API 字段解析 | `web_app.get_nmap_hosts()` | 后端参考实现 |
| 仪表盘各图表配置 | `vuetify_index.html` Vue data | 前端参考 Chart.js 配置 |
| 攻击日志页 UI 布局 | `vuetify_hfish.html` | 前端参考，用主项目 UI 组件重写 |
| 漏洞扫描页 UI 布局 | `vuetify_vuln.html` | 前端参考，用主项目 UI 组件重写 |
| 设置页漏洞规则编辑 | `vuetify_settings.html` | 前端参考，移植到 IntegrationsPage |

---

## 七、新增 API 模块建议

主项目 `frontend/src/api/` 目录需要新增/完善以下内容：

```typescript
// src/api/defense.ts 新增
getHFishLogs(params: { limit?: number; offset?: number; threat_level?: string; service_name?: string }): Promise<HFishLog[]>
getHFishStats(): Promise<HFishStats>

// src/api/scan.ts 新增
getNmapHosts(params: { scan_id?: number; state?: string; limit?: number; offset?: number }): Promise<NmapHost[]>
getNmapScans(): Promise<NmapScan[]>
getNmapHost(ip: string): Promise<NmapHost>
getNmapStats(): Promise<NmapStats>
getDiscoveredAssets(params: { mac?: string; ip?: string; limit?: number; offset?: number }): Promise<DiscoveredAsset[]>
getAssetIpHistory(assetId: number): Promise<IpHistory[]>
getVulnStats(): Promise<VulnStats>
triggerVulnScan(): Promise<void>
```

---

*文档生成时间：2026-03-06*  
*参考实现版本：ai_lzx_v2-0306*  
*主项目前端：frontend（Vue 3 + TypeScript + Vite）*
