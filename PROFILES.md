# POLYCRYINDEX Profile 契约

## 1. Profile 定义与激活机制

### 1.1 Profile 名称
项目定义两个统一的 profile：**local** 与 **cloud**。

| Profile | 部署目标 | 主要用途 |
|---------|---------|---------|
| `local` | Windows Electron 桌面版 | 单机研究环境，免登录认证 |
| `cloud` | Linux 服务器部署版 | 多用户协作环境，完整安全认证 |

### 1.2 激活方式与优先级
Profile 通过环境变量 `APP_PROFILE` 显式指定，配合运行时环境检测。

1. **主要激活器**: `APP_PROFILE` 环境变量（强制优先）
   - `APP_PROFILE=local` → local profile 激活
   - `APP_PROFILE=cloud` → cloud profile 激活
   - 未设置 → 通过运行时检测自动选择

2. **运行时检测**（当 `APP_PROFILE` 未设置时）：
   - **Electron 上下文**: 自动激活 `local` profile
   - **生产环境启动**: 自动激活 `cloud` profile  
   - **开发模式**: 默认 `local`，可通过手动设置切换

3. **配置文件支持**（降级兼容）：
   - `APP_PROFILE` 未设置时，读取 `.env` 中的 `APP_ENV`：
     - `APP_ENV=development|local` → local profile
     - `APP_ENV=beta|production` → cloud profile

### 1.3 影响范围
Profile 统一控制以下模块的配置与行为：

| 模块 | local profile 影响 | cloud profile 影响 |
|------|-------------------|-------------------|
| 后端 (FastAPI) | 认证绕过、本地用户、简化路由 | 完整认证、安全加固、生产配置 |
| 前端 (Vue) | 无登录页面、简化路由、本地标识 | 完整用户界面、登录流程 |
| Electron | 打包内置 Python 运行时、本地模式启动 | 不适用（仅 local 场景） |
| Linux 部署 | 不适用（仅 local 场景） | 一键部署脚本、systemd 配置 |
| PySide 工具 | 独立桌面应用（不受 profile 控制） | 独立桌面应用（不受 profile 控制） |

## 2. Profile 默认值与配置映射

### 2.1 核心配置映射表
每个 profile 映射到一组具体的环境变量默认值：

| 配置项 | local 默认值 | cloud 默认值 | 描述 |
|--------|-------------|-------------|------|
| **主 profile 标识** | | |
| `APP_PROFILE` | `local` | `cloud` | 主 profile 标识符 |
| `APP_ENV` | `local` | `beta` | 兼容性标识（向后兼容） |
| **认证与安全** | | |
| `AUTH_DISABLED` | `true` | `false` | 后端是否禁用认证 |
| `VITE_AUTH_DISABLED` | `true` | `false` | 前端是否显示登录界面 |
| `SECRET_KEY` | `"your-secret-key-change-in-production"` | **必须设置** | JWT 签名密钥 |
| `DEFAULT_ADMIN_PASSWORD` | `"admin123"` | **必须设置** | 管理员初始密码 |
| `LOCAL_USERNAME` | `"localuser"` | - | 本地模式用户名 |
| `LOCAL_DISPLAY_NAME` | `"Local Researcher"` | - | 本地模式显示名 |
| **服务器配置** | | |
| `HOST` | `"127.0.0.1"` | `"0.0.0.0"` | 服务监听地址 |
| `PORT` | `8000` | `8000` | 服务监听端口 |
| `LOG_LEVEL` | `"info"` | `"warning"` | 日志详细程度 |
| `ENABLE_DOCS` | `true` | `false` | 是否暴露 API 文档 |
| **路径配置** | | |
| `FORTRAN_EXECUTABLE` | 相对路径自动检测 | `/opt/polycryindex/fortrancode/lm_opt2` | 主优化程序路径 |
| `FORTRAN_POSTPROCESS_EXECUTABLE` | 相对路径自动检测 | `/opt/polycryindex/fortrancode/lm_postprocess` | 后处理程序路径 |
| **性能配置** | | |
| `MAX_JOBS` | `1` | `3` | 最大并发任务数 |
| `OMP_NUM_THREADS` | `0` | `4` | OpenMP 线程数 |

### 2.2 配置源优先级
配置按以下优先级生效：

1. **环境变量**（最高优先级） - 直接设置的值
2. **`.env` 文件** - 项目根目录下的配置文件
3. **Profile 默认值** - 如上表定义的默认值
4. **config.py 硬编码默认值**（最低优先级）

## 3. Profile 对各模块的具体影响

### 3.1 后端 (FastAPI)

#### local profile
- **认证路由**: 不注册 `/api/auth/*` 和 `/api/admin/*` 路由
- **依赖注入**: `get_current_user()` 返回预定义的本地用户对象
- **启动检查**: 跳过 SECRET_KEY 和 DEFAULT_ADMIN_PASSWORD 安全检查
- **错误处理**: 详细错误信息暴露给客户端
- **静态文件**: 从 Workspace 结构内的标准路径提供服务

#### cloud profile  
- **完整认证**: 注册所有认证和管理路由
- **安全加固**: 生产环境启动检查（拒绝默认密钥/密码）
- **错误保护**: 通用错误消息，不暴露堆栈信息
- **路径防护**: `_safe_resolve_frontend_path()` 防止路径遍历
- **静态文件**: 从标准部署路径提供服务

### 3.2 前端 (Vue)

#### local profile
- **路由配置**: 移除 `/login`、`/register`、`/admin/*` 路由
- **导航守卫**: 禁用所有路由权限检查
- **界面元素**: 隐藏用户头像、登出按钮，显示"本地研究模式"标识
- **主页设计**: 专用本地版主页（hero 面板 + 模块选择器）
- **API 基础**: 硬编码 `http://localhost:8000/api`

#### cloud profile
- **完整界面**: 标准登录/注册流程
- **权限控制**: 完整的路由守卫和权限检查
- **用户界面**: 完整的用户管理界面
- **API 基础**: 从环境变量或运行时检测获取

### 3.3 Electron 打包

#### local profile 专属
- **Python 运行时**: 内置 Python 3.9+ 解释器
- **启动配置**: `backend-manager.js` 自动设置 `APP_PROFILE=local` 和 `AUTH_DISABLED=true`
- **环境变量**: 通过 spawn 子进程传递本地模式配置
- **路径解析**: 自动检测 Workspace 结构内的运行时路径

#### cloud profile 不适用
- Electron 仅用于 local profile 打包，不参与 cloud profile 部署

### 3.4 Linux 服务器部署

#### cloud profile 专属
- **一键部署**: `deploy/server/deploy_linux.sh` 自动配置云环境
- **用户管理**: 创建专用系统用户 `polycryindex`
- **服务配置**: 安装 systemd 服务 `polycryindex.service`
- **安全配置**: 自动生成 SECRET_KEY，强制设置管理员密码
- **环境优化**: 设置 `LOG_LEVEL=warning`，禁用文档接口

#### local profile 不适用
- 服务器部署脚本仅用于 cloud profile，不参与本地开发

### 3.5 PySide 桌面工具

#### 不受 profile 控制（独立应用）
- **前处理工具** (`pyside/previous/`): 独立 WAXS 分析应用
- **后处理查看器** (`pyside/post/`): 多版本 Qt 查看器
- **启动方式**: 直接运行 Python 脚本，不依赖后端 profile
- **打包独立**: 使用 PyInstaller 单独打包为 Windows exe

## 4. 实现指引与迁移路径

### 4.1 后端迁移步骤
1. **合并 config.py**: 将历史 `localversion/backend/core/config.py` 和 `server_release/backend/core/config.py` 的差异合并到 `Workspace/backend/core/config.py`
2. **条件路由**: 基于 `APP_PROFILE` 条件注册路由
3. **依赖注入**: 基于 `APP_PROFILE` 返回不同的用户对象
4. **启动检查**: 基于 `APP_PROFILE` 执行不同的安全检查

### 4.2 前端迁移步骤  
1. **环境变量**: 支持 `VITE_APP_PROFILE` 作为 `APP_PROFILE` 的前端映射
2. **条件渲染**: 基于 `VITE_APP_PROFILE` 或 `VITE_AUTH_DISABLED` 条件渲染组件
3. **路由配置**: 动态构建路由表，基于 profile 排除特定路由
4. **API 配置**: 在 `runtime.js` 中基于 profile 选择 API 基础路径

### 4.3 Electron 适配
1. **配置传递**: `backend-manager.js` 强制设置 `APP_PROFILE=local`
2. **环境变量**: 在 spawn 时传递 `AUTH_DISABLED=true` 等本地配置
3. **路径调整**: 更新路径解析逻辑指向 Workspace 结构

### 4.4 部署脚本适配
1. **环境注入**: `deploy_linux.sh` 强制设置 `APP_PROFILE=cloud`
2. **默认值设置**: 自动配置 cloud profile 的默认值（LOG_LEVEL=warning 等）
3. **安全检查**: 保留并强化生产环境启动检查

### 4.5 构建与 CI 集成
1. **构建参数**: 在 CI 流程中通过环境变量指定 profile
2. **产物命名**: 基于 profile 生成不同的构建产物名
3. **测试策略**: 针对不同 profile 执行不同的测试集

## 5. 验证与测试清单

### 5.1 local profile 验证项
- [ ] 后端启动时自动设置 `APP_PROFILE=local`
- [ ] 前端构建时注入 `VITE_APP_PROFILE=local`
- [ ] Electron 应用启动后端时传递本地配置
- [ ] 无登录界面，直接进入工作台
- [ ] 用户身份显示为"Local Researcher"
- [ ] API 文档可访问 (`/docs`, `/redoc`)
- [ ] 详细错误信息可见

### 5.2 cloud profile 验证项
- [ ] 部署脚本自动设置 `APP_PROFILE=cloud`
- [ ] 前端构建时注入 `VITE_APP_PROFILE=cloud`
- [ ] 强制要求 SECRET_KEY 和 DEFAULT_ADMIN_PASSWORD
- [ ] 完整登录/注册流程可用
- [ ] 管理员后台功能完整
- [ ] API 文档被禁用
- [ ] 错误信息被通用化保护
- [ ] 路径遍历攻击被防护

## 6. 向后兼容与遗留支持

### 6.1 旧环境变量兼容
- `APP_ENV` 仍受支持，映射到 profile：
  - `development|local` → `local` profile
  - `beta|production` → `cloud` profile
- `AUTH_DISABLED` 仍受支持，但推荐使用 `APP_PROFILE`
- `VITE_AUTH_DISABLED` 仍受支持，但推荐使用 `VITE_APP_PROFILE`

### 6.2 旧目录结构兼容
- `server_release/` 作为 legacy 参考；`localversion/` 的 Electron 活动树内旧快照已移除
- 新实现基于 `Workspace/` 统一源码树
- 构建和部署脚本逐步迁移到新结构

---

## 附录：Profile 切换示例

### 开发环境切换到 cloud profile
```bash
# 临时测试 cloud 配置
APP_PROFILE=cloud python -m uvicorn main:app --reload

# 永久设置（编辑 .env）
APP_PROFILE=cloud
```

### 构建时指定 profile
```bash
# 前端构建
VITE_APP_PROFILE=cloud npm run build

# Electron 打包（总是 local）
npm run electron:build
```

### 部署脚本强制 cloud
```bash
# deploy_linux.sh 内部
export APP_PROFILE=cloud
export LOG_LEVEL=warning
export ENABLE_DOCS=false
```
