# 🔥 AimiGuard (智能安全与资产监控平台)

**AimiGuard** 是一个基于全新 MVC 架构重构的现代原生主机安全、资产发现与威胁监控平台。它将 **Nmap (网络发现与漏洞扫描)** 与 **HFish (蜜罐攻击日志)** 深度整合，并通过一套美观且响应式的 Vue + Vuetify 前端界面，为你提供企业级的内部安全资产大屏展示。

---


### ✨ 核心功能亮点
1. **自动资产测绘与 OS 标签**：不仅能扫出内网主机和开放端口服务，还能自动将庞杂的 Nmap 操作系统指纹标准化（如 `windows 10`, `linux`, `bsd`），方便分类。
2. **智能化漏洞探测 (NSE)**：根据主机的 OS 标签，自动挂载并下发对应的专属 Nmap Vulnerability 探测脚本（如只对老旧组件跑特定的 MS 漏洞扫描），大大提高扫描精度和效率。
3. **威胁情报中枢 (HFish)**：自动提取 HFish 蜜罐中高价值的攻击行为日志并做图表化分析，随时掌控内网横向移动痕迹。
4. **全自动后台轮询**：Nmap 漏洞资产扫描与 HFish 攻击拦截均在 Python 守护线程中自动静默运行（按你设定的间隔时间）。

---

## 📂 目录结构

```text
aimiguard/
├── config.json              # 核心配置文件 (服务、Nmap、HFish、白名单等)
├── README.md                # 项目文档
├── database/                # 模型与数据库层 [M]
│   ├── db.py                # 底层 sqlite 游标连接与初始化 (创建库结构)
│   ├── models.py            # 面向对象的查询/写入接口层
│   └── aimiguard.db         # (运行后自动生成) 全局统一数据库
├── hfish/                   # 蜜罐子系统
│   └── attack_log_sync.py   # API 对接及格式化程序
├── nmap/                    # 扫描与测绘子系统
│   └── network_scan.py      # 主机存活、端口及 NSE 漏洞执行器
└── web/                     
    ├── web_app.py           # Web 控制器与 API 层 [C]
    └── templates/           # 前端大屏视图代码 [V] (基于 Vuetify)
```

---

## ⚙️ 快速开始

### 1. 环境准备
一台装有 **Python 3.8+** 以及 **Nmap** (必须被添加至系统环境变量) 的主机。

```bash
# 安装 Python 依赖
pip install flask python-nmap
```

*(注意：如果你的网络环境需要，请解决 `github` 或其他源的连通性)*

### 2. 基础配置
在项目根目录下创建/修改 `config.json`，**必须**包含以下核心节点，否则安全防御机制将拒绝系统启动：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
  },
  "nmap": {
    "ip_ranges": ["192.168.1.1/24"],
    "arguments": "-sS -O -T4",
    "scan_interval": 86400,
    "scan_enabled": true
  },
  "hfish": {
    "host_port": "127.0.0.1:4433",
    "api_key": "YOUR_API_KEY",
    "sync_interval": 300,
    "sync_enabled": true
  },
  "vuln_scripts": {
    "VULN_SCRIPTS_BY_TAG": {
      "windows": ["smb-vuln-ms17-010"]
    },
    ...
  }
}
```

### 3. 一键启动
```bash
python web/web_app.py
```
> 如果是在 Windows 平台，此时可能会弹窗请求 Nmap 的管理员网络权限，请点击"允许"。

打开浏览器，访问 `http://localhost:5000` (或你在配置里设置的端口)，即可看到 AimiGuard 控制台。

---

## 🛠️ API 开发指南

得益于新架构，你可以轻松对接第三方平台（返回标准 JSON 结构）：

| 模块  | 接口地址 | 请求方式 | 作用说明 |
| :--- | :--- | :--- | :--- |
| **看板** | `/api/settings` <br/> `/api/nmap/stats` | GET / POST | 获取/修改配置策略，获取平台大盘存活基础统计 |
| **资产** | `/api/nmap/hosts` <br/> `/api/nmap/assets` | GET | 按照 `scan_id` 获取资产明细，以及被追踪的高级资产池 |
| **漏洞** | `/api/nmap/vuln` <br/> `/api/nmap/vuln/scan` | GET / POST | 获取漏洞扫描明细，或手动启动全局深度 NSE 漏洞扫描 |
| **情报** | `/api/hfish/logs` | GET | 分页获取并检索从 HFish 蜜罐收集到的攻击数据 |

---

## 👨‍💻 后续演进规划 (Roadmap)
- [x] 基于模型层 (MVC) 的底层大重构
- [x] 实现主机操作系统的智能聚类标签机制
- [ ] 🤖 **接入 LLM (大模型) 安全防守大师功能**
- [ ] 提供主机上线/漏洞触发时的钉钉/飞书 Webhook 实时告警
- [ ] 导出 PDF 企业网络安全体检报告
