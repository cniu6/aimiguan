# Aimiguan 快速启动指南

## 环境要求

- Python 3.9+
- Node.js 18+
- SQLite 3

## 后端启动

### 1. 安装依赖

```powershell
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
cp .env.example .env
# 编辑 .env 文件，修改必要的配置
```

### 3. 初始化数据库

```powershell
python init_db.py
```

### 4. 启动后端服务

```powershell
python main.py
```

后端服务将在 http://localhost:8000 启动

## 前端启动

### 1. 安装依赖

```powershell
cd frontend
npm install
```

### 2. 配置环境变量

```powershell
cp .env.example .env
# 编辑 .env 文件（可选）
```

### 3. 启动开发服务器

```powershell
npm run dev
```

前端服务将在 http://localhost:3000 启动

## 访问应用

打开浏览器访问：http://localhost:3000

## API 文档

访问 http://localhost:8000/docs 查看 API 文档

## 目录结构

```
aimiguan/
├── backend/              # 后端代码
│   ├── api/             # API 路由
│   ├── core/            # 核心模块（数据库）
│   ├── services/        # 业务服务
│   └── main.py          # 入口文件
├── frontend/            # 前端代码
│   ├── src/
│   │   ├── api/        # API 客户端
│   │   ├── views/      # 页面组件
│   │   ├── router/     # 路由配置
│   │   └── main.ts     # 入口文件
│   └── package.json
└── README.md           # 完整文档
```

## 功能模块

- **防御监控** (`/defense`) - 威胁事件处置
- **扫描管理** (`/scan`) - 资产扫描与漏洞管理
- **AI 中枢** (`/ai`) - AI 对话与报告生成

## 故障排查

### 后端无法启动

1. 检查 Python 版本：`python --version`
2. 检查依赖安装：`pip list`
3. 检查数据库文件权限

### 前端无法启动

1. 检查 Node.js 版本：`node --version`
2. 清除缓存：`npm cache clean --force`
3. 重新安装：`rm -rf node_modules && npm install`

### API 调用失败

1. 检查后端服务是否运行
2. 检查 CORS 配置
3. 查看浏览器控制台错误信息

## 下一步

参考 [README.md](./README.md) 了解完整的架构设计和实施计划。