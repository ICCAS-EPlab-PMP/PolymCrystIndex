# PolymCrystIndex 参考文档 / Reference

> 纤维衍射图谱指标化平台 v1.8.3
>
> **技术栈**: Vue.js 3 (前端) + FastAPI (后端) + Fortran (核心算法)

---

## 0. 使用说明 / How to Use This Document

`README.md` 负责项目首页式介绍，聚焦项目目标、用户群体、安装方式、示例流程与引用信息；本文件保留结构化参考内容，便于开发、部署、排查和接口查阅。

`README.md` is the landing page for project goals, audience, installation, workflow examples, and citation. This document keeps the structure-heavy reference material for development, deployment, troubleshooting, and API lookup.

### 0.1 仓库结构简表 / Repository Structure at a Glance

| 路径 | 作用 |
|---|---|
| `backend/` | FastAPI 后端、认证、任务调度、结果接口 |
| `frontend/` | Vue 3 前端界面与交互逻辑 |
| `electron/` | Windows 桌面版打包链 |
| `fortrancode/` | 核心 Fortran 优化与后处理程序 |
| `fiber_diffraction_indexing/` | 可复用 Python 包与命令行能力 |
| `pyside/` | 辅助前后处理与调试工具 |
| `deploy/` | Linux 部署脚本、systemd 模板与运维文档 |
| `PROFILES.md` / `deploy/README.md` / `pyside/README.md` / `fiber_diffraction_indexing/docs/` | 运行配置、部署、辅助工具与 Python 包文档 |
| `EXAMPLE/` | 示例数据与结果 |

### 0.2 阅读建议 / Reading Guide

- 想快速了解项目：先看 `README.md`
- 想看部署步骤：看 `deploy/README.md`
- 想查模块或接口：继续阅读本文件后续章节
- 想看示例数据：看 `EXAMPLE/`

## 1. 前端文件与界面对应

### 1.1 页面路由 (`frontend/src/views/`)

| 界面名称 | 路由路径 | 文件路径 |
|---------|---------|---------|
| 登录页 | `/login` | `src/views/Login.vue` |
| 首页（模块选择） | `/app/home` | `src/views/Home.vue` |
| 指标化程序主页 | `/app/indexing` | `src/views/IndexingPage.vue` |
| 衍射峰提取 | `/app/peak-extraction` | `src/views/PeakExtractionPage.vue` |
| 结果展示 | `/app/results` | `src/views/ResultsPage.vue` |
| 关于页面 | - | `src/views/About.vue` |
| 管理员概览 | `/admin` | `src/views/AdminPage.vue` |
| 用户管理 | `/admin/users` | `src/views/admin/Users.vue` |
| 任务审计 | `/admin/tasks` | `src/views/admin/Tasks.vue` |
| 系统状态 | `/admin/system` | `src/views/admin/SystemStatus.vue` |

### 1.2 可复用组件 (`frontend/src/components/`)

| 组件名称 | 文件路径 | 功能说明 |
|---------|---------|---------|
| 数据导入 | `src/components/DataImport.vue` | 文件上传与格式验证 |
| 参数设置 | `src/components/ParamsSetup.vue` | 晶胞参数配置 |
| 分析控制台 | `src/components/Console.vue` | 实时日志输出 |
| 结果导出 | `src/components/ResultExport.vue` | ZIP/CSV 导出 |
| 3D 可视化 | `src/components/Visualizer.vue` | Plotly.js 3D 结构 |
| 图像画布 | `src/components/ImageCanvas.vue` | 底层的像素渲染 |
| 原始图像视图 | `src/components/RawView.vue` | EDF/TIFF 显示 |
| 积分图像视图 | `src/components/IntView.vue` | 积分结果展示 |
| 服务器状态 | `src/components/ServerStatus.vue` | 连接状态指示 |
| 确认对话框 | `src/components/ConfirmDialog.vue` | 操作确认弹窗 |

### 1.3 布局组件 (`frontend/src/layouts/`)

| 布局名称 | 文件路径 | 适用对象 |
|---------|---------|---------|
| 用户布局 | `src/layouts/UserLayout.vue` | 普通用户（含顶部栏、国际化切换） |
| 管理员布局 | `src/layouts/AdminLayout.vue` | 管理员（含侧边栏导航） |

### 1.4 API 客户端 (`frontend/src/api/`)

| API 模块 | 文件路径 | 功能说明 |
|---------|---------|---------|
| 主 API 封装 | `src/api/index.js` | 所有后端接口的统一封装 |
| 请求拦截器 | `src/api/request.js` | Axios 配置、Token 注入、错误处理 |
| 峰提取 API | `src/api/peakExtractionApi.js` | 原始/积分图像峰提取接口 |

### 1.5 Composables (`frontend/src/composables/`)

| Composable | 文件路径 | 功能说明 |
|---|---|---|
| 管理员确认弹窗 | `src/composables/useAdminConfirm.js` | ConfirmDialog + showAlert 逻辑复用 |
| 自动刷新 | `src/composables/useAutoRefresh.js` | 定时自动刷新逻辑复用 |
| 分页 | `src/composables/usePagination.js` | 分页状态与计算复用 |

### 1.6 工具函数 (`frontend/src/utils/diffraction/`)

| 工具 | 文件路径 | 功能说明 |
|-----|---------|---------|
| 衍射工具入口 | `src/utils/diffraction/index.js` | 导出所有衍射相关工具 |
| 像素坐标计算 | `src/utils/diffraction/PixelCoordinateCalc.js` | 晶格像素位置计算 |
| Miller 文件解析 | `src/utils/diffraction/MillerFileParser.js` | Miller 索引文件解析 |
| 色彩映射渲染 | `src/utils/diffraction/ColormapRenderer.js` | 图像伪彩色映射 |

### 1.7 路由配置 (`frontend/src/router/`)

| 文件 | 功能说明 |
|------|---------|
| `index.js` | 路由入口、守卫配置 |
| `modules/user.js` | 用户端路由模块 |
| `modules/admin.js` | 管理端路由模块 |

### 1.8 状态管理 (`frontend/src/stores/`)

| Store | 文件路径 | 功能说明 |
|-------|---------|---------|
| 认证状态 | `src/stores/auth.js` | 登录状态、Token、权限列表存储 |

### 1.9 服务层 (`frontend/src/services/`)

| 服务 | 文件路径 | 功能说明 |
|------|---------|---------|
| 权限判断 | `src/services/permission.js` | hasPermission / hasRole（从 auth store 读取权限） |
| Admin API | `src/services/admin.js` | 管理端 API 封装（14 个方法） |
| 运行时抽象 | `src/services/runtime.js` | Web/Electron 环境识别、API base 配置 |
| 存储抽象 | `src/services/storage.js` | localStorage 包装，支持未来 IPC 切换 |

### 1.10 国际化 (`frontend/src/i18n/`)

| 文件 | 功能说明 |
|------|---------|
| `en.js` | 英文语言包 |
| `zh.js` | 中文语言包 |
| `index.js` | i18n 配置入口 |

### 1.11 样式 (`frontend/src/styles/`)

| 文件 | 功能说明 |
|------|---------|
| `global.css` | 全局样式 |
| `variables.css` | CSS 变量定义 |

### 1.12 应用入口 (`frontend/src/`)

| 文件 | 功能说明 |
|------|---------|
| `main.js` | Vue 应用入口 |
| `App.vue` | 根组件 |

---

## 2. 后端文件与功能对应

### 2.1 应用入口

| 文件 | 路径 | 功能说明 |
|-----|------|---------|
| FastAPI 入口 | `backend/main.py` | 应用创建、路由注册、中间件配置、前端静态托管（HTML 入口禁缓存，减少单端口部署时页面切换触发的 304 校验干扰） |
| 生产启动入口 | `backend/run_prod.py` | 单进程生产模式启动（uvicorn，no reload） |
| 依赖配置 | `backend/core/dependencies.py` | 依赖注入（数据库连接、当前用户） |
| 应用配置 | `backend/core/config.py` | 路径、密钥、环境、CORS、Fortran 路径等配置项 |

### 2.2 API 路由 (`backend/api/`)

| 路由文件 | 路由前缀 | 功能说明 |
|---------|---------|---------|
| `auth.py` | `/api/auth` | 登录、注册、获取当前用户信息 |
| `data.py` | `/api/data` | 数据文件验证与上传 |
| `analysis.py` | `/api/analysis` | 分析任务控制（启动/状态/日志/取消） |
| `results.py` | `/api/results` | 结果查询与下载 |
| `visualizer.py` | `/api/visualizer` | 可视化数据（PONI 解析、图像） |
| `status.py` | `/api/status` | 服务器健康状态 |
| `peak_raw.py` | `/api/peak/raw` | 原始图像峰提取 |
| `peak_integrated.py` | `/api/peak/integrated` | 积分图像寻峰 |
| `admin/users.py` | `/api/admin/users` | 用户管理（增删改查） |
| `admin/tasks.py` | `/api/admin/tasks` | 任务审计日志 |
| `admin/dashboard.py` | `/api/admin/dashboard` | 仪表盘统计数据 |
| `admin/system.py` | `/api/admin/system` | 系统配置管理 |

### 2.3 业务逻辑服务 (`backend/services/`)

| 服务文件 | 功能说明 |
|---------|---------|
| `auth_service.py` | JWT Token 生成与验证 |
| `user_service.py` | 用户 CRUD 操作 |
| `task_manager.py` | 任务队列管理、进程控制 |
| `indexing_service.py` | **核心索引服务**：协调 Python 和 Fortran 程序 |
| `diffraction_utils.py` | 衍射几何计算工具库 |
| `image_service.py` | 图像处理（EDF/TIFF 读取） |
| `file_service.py` | 文件 I/O 操作 |
| `physics.py` | 散射几何和物理计算 |
| `session_store.py` | 会话数据存储 |
| `system_config_service.py` | 系统配置服务 |

### 2.3.1 数据访问层 (`backend/repositories/`)

| 文件 | 功能说明 |
|-----|---------|
| `user_repository.py` | 用户 SQLite 数据库操作（CRUD、初始化） |
| `system_config_repository.py` | 系统配置数据访问 |

### 2.3.2 工具模块 (`backend/utils/`)

| 文件 | 功能说明 |
|-----|---------|
| `hdf5_utils.py` | HDF5 文件读写工具（晶胞参数读取等） |

### 2.4 数据模型 (`backend/models/`)

| 模型文件 | 功能说明 |
|---------|---------|
| `auth.py` | 登录请求、Token 响应模型 |
| `user.py` | 用户数据模型 |
| `admin_user.py` | 管理员用户扩展模型 |
| `analysis.py` | 分析参数模型 |
| `admin_task.py` | 任务审计模型 |
| `data.py` | 数据上传相关模型 |
| `results.py` | 结果数据模型 |
| `system_config.py` | 系统配置模型 |

### 2.5 核心配置 (`backend/core/`)

| 配置文件 | 功能说明 |
|---------|---------|
| `config.py` | 全局配置（路径、密钥、APP_ENV、CORS、Fortran 跨平台路径、OMP_NUM_THREADS） |
| `security.py` | JWT 安全工具、密码哈希 |
| `dependencies.py` | FastAPI 依赖注入 |
| `permissions.py` | 权限检查装饰器 |

### 2.6 新增文件（Phase 8）

| 文件 | 功能说明 |
|------|---------|
| `backend/run_prod.py` | 单进程生产模式启动入口 |
| `backend/.env.example` | 环境变量配置模板 |
| `frontend/.env.production` | 前端生产环境变量 |
| `deploy/README.md` | 部署指南 |
| `deploy/server/deploy_linux.sh` | root/systemd 部署脚本 |
| `deploy/server/install_user_linux.sh` | 当前用户部署脚本 |
| `deploy/systemd/polycryindex.service` | systemd 服务单元 |

---

## 3. 其他文件夹功能

### 3.1 `fortrancode/` - Fortran 核心算法

Levenberg-Marquardt 优化算法实现，包含主程序 `lm_opt2`/`lm_opt2.exe`、后处理程序 `lm_postprocess`/`lm_postprocess.exe` 及相关模块。Linux 迁移版本已将命令行文件名缓冲区扩展到 512 字符，并配合 Python 相对路径调用，避免 `diffraction.txt` 被截断为 `diffractio` 一类问题。

### 3.2 `fiber_diffraction_indexing/` - Python 索引包

| 文件 | 功能说明 |
|-----|---------|
| `fiberdiffraction/indexer.py` | **主协调器类**（遗传算法 + Fortran 调用） |
| `fiberdiffraction/genetic.py` | 遗传算法引擎 |
| `fiberdiffraction/population.py` | 种群管理 |
| `fiberdiffraction/fortran.py` | Fortran 程序调用封装（按任务工作目录内的相对文件名调用 `input.txt`、`diffraction.txt`、`cell_N.txt`，避免 Linux 长绝对路径被截断） |
| `fiberdiffraction/fileio.py` | 文件读写操作 |
| `fiberdiffraction/hdf5.py` | HDF5 数据存储 |
| `fiberdiffraction/plotter.py` | 图表生成 |
| `fiberdiffraction/callbacks.py` | 进度回调接口 |
| `fiberdiffraction/cli.py` | 命令行入口 |
| `fiberdiffraction/config.py` | 输入配置解析 |
| `fiberdiffraction/__init__.py` | 包初始化 |
| `fiberdiffraction/__main__.py` | `python -m` 入口 |
| `fiberdiffraction/version.py` | 版本号定义 |
| `config/input_template.txt` | 输入配置模板 |
| `scripts/diffraction_fiber.py` | 衍射计算脚本 |
| `scripts/initial.py` | 初始参数生成脚本 |
| `scripts/sort.py` | 排序工具脚本 |

### 3.3 文档与配置说明

| 文件 | 功能说明 |
|-----|---------|
| `Reference.md` | 仓库总体参考文档 |
| `PROFILES.md` | 本地 / 云端 profile 与环境变量行为说明 |
| `deploy/README.md` | Linux 部署与运维说明 |
| `pyside/README.md` | PySide 工具与打包说明 |
| `fiber_diffraction_indexing/docs/user_guide.md` | Python 指标化包使用指南 |
| `fiber_diffraction_indexing/docs/api_reference.md` | Python 指标化包 API 参考 |

### 3.4 `frontend/` - 前端资源

| 目录/文件 | 功能说明 |
|---------|---------|
| `src/` | Vue.js 源码 |
| `public/` | 静态资源 |
| `package.json` | Node.js 依赖 |
| `vite.config.js` | Vite 构建配置 |

### 3.5 `backend/` - 后端资源

| 目录/文件 | 功能说明 |
|---------|---------|
| `api/` | API 路由 |
| `services/` | 业务逻辑 |
| `models/` | 数据模型 |
| `core/` | 核心配置 |
| `repositories/` | 数据访问层 |
| `utils/` | 工具模块 |

### 3.6 `deploy/` - 部署资产

| 目录/文件 | 功能说明 |
|----------|---------|
| `deploy/README.md` | 部署指南（环境要求、步骤、配置说明、问题排查） |
| `deploy/server/deploy_linux.sh` | root/systemd 模式部署脚本 |
| `deploy/server/install_user_linux.sh` | 当前用户模式部署脚本 |
| `deploy/systemd/polycryindex.service` | systemd 服务单元文件 |

### 3.7 根目录目录/文件

| 目录/文件 | 功能说明 |
|----------|---------|
| `EXAMPLE/` | 示例数据目录 |
| `icon/` | 应用图标资源 |
| `.github/` | GitHub Actions 等仓库自动化配置 |
| `PROFILES.md` | profile 与环境配置说明 |
| `Reference.md` | 结构化参考文档 |
| `README.md` | 项目说明 |

---

## 4. 系统架构流程

### 4.1 单端口部署架构（Phase 8）

```
┌─────────────────────────────────────────────────────────────┐
│  浏览器 (http://server:8000)                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           FastAPI (端口 8000)                        │    │
│  │                                                     │    │
│  │  /api/*  → 后端 API 路由                            │    │
│  │  /docs   → Swagger 文档                             │    │
│  │  /redoc  → ReDoc 文档                               │    │
│  │  /health → 部署级健康检查                            │    │
│  │  /*      → SPA fallback → frontend/dist/index.html  │    │
│  │           (Cache-Control: no-store)                 │    │
│  │  /assets → frontend/dist/assets/ (静态资源)          │    │
│  └─────────────────────────────────────────────────────┘    │
│                         │                                   │
│         ┌───────────────┼───────────────┐                  │
│         │  Vue.js SPA   │   API 路由     │                  │
│         │  (前端 dist)   │               │                  │
│         └───────────────┘               │                  │
│                           ┌─────────────┴─────────────┐    │
│                           │  indexing_service          │    │
│                           │  task_manager              │    │
│                           └─────────────┬─────────────┘    │
│                                         │ subprocess        │
│                           ┌─────────────┴─────────────┐    │
│                           │  Fortran (lm_opt2)         │    │
│                           │  相对路径读取任务输入文件   │    │
│                           │  Levenberg-Marquardt 优化   │    │
│                           └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 开发模式架构（前后端分离）

```
┌─────────────────────────────────────────────────────────────┐
│  Vue.js Frontend (端口 5173)                                 │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌───────────┐  │
│  │Login.vue│  │Indexing  │  │PeakExtract │  │Results    │  │
│  │Home.vue │  │Page.vue  │  │Page.vue    │  │Page.vue   │  │
│  └────┬────┘  └────┬─────┘  └─────┬──────┘  └─────┬─────┘  │
└───────┼───────────┼──────────────┼───────────────┼────────┘
        │           │              │               │
        └───────────┴──────────────┴───────────────┘
                    HTTP REST API
        ┌───────────────────────────────────┐
        │       FastAPI Backend (端口 8000)  │
        │  ┌─────────┐  ┌─────────────────┐ │
        │  │auth.py  │  │ analysis.py     │ │
        │  │data.py  │  │indexing_service │ │
        │  │results  │  │ task_manager    │ │
        │  └────┬────┘  └────────┬────────┘ │
        └───────┼────────────────┼──────────┘
                │                │
        ┌───────┴────────────────┴───────┐
        │   Python Middle Layer          │
        │  fiber_diffraction_indexing/  │
        │  (遗传算法 + 流程协调)         │
        └───────────────┬────────────────┘
                        │ subprocess
        ┌───────────────┴───────────────┐
        │   Fortran Core (lm_opt2)      │
        │   相对路径读取任务输入        │
        │   Levenberg-Marquardt 优化    │
        └───────────────────────────────┘
```
┌─────────────────────────────────────────────────────────────┐
│  Vue.js Frontend (端口 5173)                                 │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌───────────┐  │
│  │Login.vue│  │Indexing  │  │PeakExtract │  │Results    │  │
│  │Home.vue │  │Page.vue  │  │Page.vue    │  │Page.vue   │  │
│  └────┬────┘  └────┬─────┘  └─────┬──────┘  └─────┬─────┘  │
└───────┼───────────┼──────────────┼───────────────┼────────┘
        │           │              │               │
        └───────────┴──────────────┴───────────────┘
                    HTTP REST API
        ┌───────────────────────────────────┐
        │       FastAPI Backend (端口 8000)  │
        │  ┌─────────┐  ┌─────────────────┐ │
        │  │auth.py  │  │ analysis.py     │ │
        │  │data.py  │  │indexing_service │ │
        │  │results  │  │ task_manager    │ │
        │  └────┬────┘  └────────┬────────┘ │
        └───────┼────────────────┼──────────┘
                │                │
        ┌───────┴────────────────┴───────┐
        │   Python Middle Layer          │
        │  fiber_diffraction_indexing/  │
        │  (遗传算法 + 流程协调)         │
        └───────────────┬────────────────┘
                        │ subprocess
        ┌───────────────┴───────────────┐
        │   Fortran Core (lm_opt2.exe)  │
        │   相对路径读取任务输入        │
        │   Levenberg-Marquardt 优化    │
        └───────────────────────────────┘
```

---

## 5. API 端点速查

### 5.0 部署级端点

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/health` | 部署级健康检查（app_env、Fortran 状态、目录可写性、运行任务数） |

### 5.1 认证相关 `/api/auth`

| 方法 | 端点 | 功能 |
|-----|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| GET | `/api/auth/me` | 获取当前用户 |

### 5.2 数据处理 `/api/data`

| 方法 | 端点 | 功能 |
|-----|------|------|
| POST | `/api/data/check` | 验证数据文件 |
| POST | `/api/data/upload` | 上传数据文件 |

### 5.3 分析任务 `/api/analysis`

| 方法 | 端点 | 功能 |
|-----|------|------|
| POST | `/api/analysis/run` | 启动分析任务 |
| GET | `/api/analysis/status/{id}` | 获取任务状态 |
| GET | `/api/analysis/logs/{id}` | 获取任务日志 |
| POST | `/api/analysis/cancel/{id}` | 取消任务 |

### 5.4 结果 `/api/results`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/results` | 获取结果列表 |
| GET | `/api/results/download?type=zip&task_id=xxx` | 下载结果文件（type: zip/hdf5/cell/miller） |

### 5.5 可视化 `/api/visualizer`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/visualizer/status` | 可视化器状态（版本、依赖、已加载数据） |
| POST | `/api/visualizer/raw/upload-image` | 上传原始衍射图像（.tif/.edf/.cbf） |
| POST | `/api/visualizer/raw/upload-poni` | 上传 PONI 文件，提取仪器参数 |
| POST | `/api/visualizer/raw/upload-miller` | 上传 Miller 文件（full/output） |
| DELETE | `/api/visualizer/raw/miller` | 清除 Miller 标记点 |
| POST | `/api/visualizer/raw/image-only` | 仅返回纯图像（无标记） |
| POST | `/api/visualizer/raw/markers` | 仅返回 Miller 标记点坐标 |
| POST | `/api/visualizer/raw/render` | 渲染原始衍射图（含 Miller 标记） |
| POST | `/api/visualizer/int/upload-image` | 上传 2D 积分图像（.npy/.tif） |
| POST | `/api/visualizer/int/upload-info` | 上传 processing_info.txt，提取坐标范围 |
| POST | `/api/visualizer/int/upload-miller` | 上传 Miller 文件（2D 积分图用） |
| DELETE | `/api/visualizer/int/miller` | 清除 Miller 标记点 |
| PUT | `/api/visualizer/int/coordinate-ranges` | 更新 q/azimuth 坐标范围 |
| POST | `/api/visualizer/int/render` | 渲染 2D 积分图（含 Miller 标记） |

### 5.6 峰提取 `/api/peak/*`

#### 5.6.1 原始图像 `/api/peak/raw`

| 方法 | 端点 | 功能 |
|-----|------|------|
| POST | `/api/peak/raw/load` | 加载原始 EDF/TIFF 图像 |
| POST | `/api/peak/raw/import-poni` | 导入 PONI 文件，返回仪器参数 |
| POST | `/api/peak/raw/render` | 重新渲染图像（色图/对比度） |
| POST | `/api/peak/raw/apply-threshold` | 应用阈值过滤 |
| POST | `/api/peak/raw/click` | 点击主图选峰（返回放大视图 + q/ψ） |
| POST | `/api/peak/raw/zoom-click` | 点击放大图精确定位 |
| POST | `/api/peak/raw/integrate` | pyFAI 1D 径向 + 方位角积分 |
| POST | `/api/peak/raw/record-point` | 记录选中的峰位 |
| POST | `/api/peak/raw/delete-record` | 删除单条记录 |
| POST | `/api/peak/raw/clear-records` | 清空所有记录 |
| POST | `/api/peak/raw/calc-pixel` | 从 q/ψ 计算像素坐标 |
| GET | `/api/peak/raw/export-csv/{session_id}` | 导出 CSV（含原始和校正 ψ） |
| GET | `/api/peak/raw/export-txt/{session_id}` | 导出 TXT（q ψ 1 三列） |

#### 5.6.2 积分图像 `/api/peak/integrated`

| 方法 | 端点 | 功能 |
|-----|------|------|
| POST | `/api/peak/integrated/load` | 加载 2D 积分图像（.npy/.tif） |
| POST | `/api/peak/integrated/import-info` | 导入 processing_info.txt，提取坐标范围 |
| POST | `/api/peak/integrated/set-ranges` | 更新坐标范围 |
| POST | `/api/peak/integrated/import-miller` | 导入 Miller 索引文件 |
| POST | `/api/peak/integrated/transform-miller` | 按约定/参考角变换 Miller 坐标 |
| POST | `/api/peak/integrated/get-slice` | 获取 q-slice 和 azimuth-slice |
| POST | `/api/peak/integrated/find-peaks` | 自动寻峰（支持 crop） |
| POST | `/api/peak/integrated/record-peaks` | 记录选中的峰 |
| POST | `/api/peak/integrated/delete-record` | 删除单条记录 |
| POST | `/api/peak/integrated/clear-records` | 清空所有记录 |
| GET | `/api/peak/integrated/export-csv/{session_id}` | 导出 CSV |

### 5.7 管理端 `/api/admin/*`

#### 5.7.1 用户管理 `/api/admin/users`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/admin/users` | 用户列表（含已禁用） |
| POST | `/api/admin/users` | 创建用户 |
| PATCH | `/api/admin/users/{user_id}` | 更新用户信息（角色/显示名/状态） |
| POST | `/api/admin/users/{user_id}/disable` | 禁用用户（软删除） |
| POST | `/api/admin/users/{user_id}/enable` | 启用用户 |
| POST | `/api/admin/users/{user_id}/reset-password` | 重置用户密码 |

#### 5.7.2 任务审计 `/api/admin/tasks`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/admin/tasks` | 任务审计列表（可按 user_id/status 过滤） |
| GET | `/api/admin/tasks/{task_id}` | 获取任务详情 |
| GET | `/api/admin/tasks/{task_id}/logs` | 获取任务日志 |
| POST | `/api/admin/tasks/{task_id}/cancel` | 取消任务 |

#### 5.7.3 仪表盘 `/api/admin/dashboard`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/admin/dashboard` | 仪表盘统计数据 |

#### 5.7.4 系统配置 `/api/admin/system`

| 方法 | 端点 | 功能 |
|-----|------|------|
| GET | `/api/admin/system` | 获取系统配置列表 |
| PUT | `/api/admin/system/{key}` | 更新指定配置项 |

---

## 6. 关键类/函数说明

### 6.1 后端核心服务

**indexing_service.py - IndexingService**
```
作用: 协调整个指标化流程
流程: 初始化 → 遗传算法循环 → Fortran 优化 → 后处理 → 生成图表
```

**task_manager.py - TaskManager**
```
作用: 管理后台分析任务的生命周期
方法: run_task(), get_status(), cancel_task(), get_logs()
```

**fortran.py - FortranRunner**
```
作用: 封装 Fortran 程序调用
方法: run(), check_convergence(), parse_output()
```

### 6.2 前端核心组件

**IndexingPage.vue**
```
作用: 指标化主界面
子组件: DataImport, ParamsSetup, Console, Visualizer, ResultExport
```

**PeakExtractionPage.vue**
```
作用: 衍射峰提取界面
子组件: RawView, IntView, ImageCanvas
```

---

## 7. 数据流向

### 7.1 指标化流程数据流

```
用户上传 EDF/TIFF 图像
    ↓
backend/api/data.py (验证) → backend/temp/
    ↓
backend/api/analysis.py (启动任务)
    ↓
fiber_diffraction_indexing/indexer.py (协调)
    ↓
fortrancode/lm_opt2 / lm_opt2.exe (L-M 优化，按任务工作目录中的相对文件名读取输入)
    ↓
backend/result/ (ZIP 结果)
    ↓
frontend/ResultsPage.vue (展示)
```

### 7.2 峰提取数据流

```
用户上传 EDF/TIFF → backend/temp/
    ↓
/api/peak/raw/load → ImageService → Base64 返回
    ↓
用户点击选择峰 → /api/peak/raw/click → 峰位记录
    ↓
/api/peak/raw/integrate → pyFAI 2D 积分
    ↓
/api/peak/integrated/find-peaks → 峰列表返回
```

---

*文档生成时间: 2026-04-02*
