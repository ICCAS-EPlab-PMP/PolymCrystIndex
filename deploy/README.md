# PolyCryIndex 部署指南

## 服务器环境要求

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| 操作系统 | Rocky 9 / Ubuntu 20.04+ / CentOS 7+ | 运行环境 |
| Python | 3.9+ | 后端运行时 |
| Node.js | 16+ | 构建 `Workspace/frontend` |
| gfortran | 任意可用版本 | 编译 `Workspace/fortrancode` |

## 源码与安装语义

- 仓库内唯一权威源码入口：`Workspace/`
- Linux 部署脚本入口：`Workspace/deploy/server/*.sh`
- 安装后保持 Workspace 语义：`/opt/polycryindex/Workspace/...`
- `APP_PROFILE` 是主 profile 入口；Linux 部署固定写入 `APP_PROFILE=cloud`
- `APP_ENV` 仅保留兼容；默认写入 `beta`

## 安装目录标准

```text
/opt/polycryindex/
├── Workspace/
│   ├── backend/
│   │   ├── .env
│   │   ├── run_prod.py
│   │   ├── temp/
│   │   ├── result/
│   │   ├── hdf5/
│   │   ├── userresult/
│   │   ├── workdir/
│   │   └── figures/
│   ├── frontend/
│   │   └── dist/
│   ├── fortrancode/
│   │   ├── lm_opt2
│   │   └── lm_postprocess
│   ├── fiber_diffraction_indexing/
│   └── deploy/
│       └── systemd/
│           └── polycryindex.service
├── venv/
└── logs/
```

## 推荐方式：一键部署

### root / systemd 方式

```bash
cd Workspace/deploy/server
sudo APP_PROFILE=cloud bash ./deploy_linux.sh
```

### 当前用户方式

```bash
cd Workspace/deploy/server
APP_PROFILE=cloud bash ./install_user_linux.sh
```

脚本会自动完成：

1. 从当前仓库 `Workspace/` 复制源码到安装目录中的 `Workspace/`
2. 创建 `venv/` 并安装 `Workspace/backend/requirements.txt`
3. 编译 `Workspace/fortrancode/` 中的 Fortran 程序
4. 以 `VITE_APP_PROFILE=cloud` 构建 `Workspace/frontend/`
5. 生成 `Workspace/backend/.env`
6. 启动 `run_prod.py` 并执行 `http://127.0.0.1:8000/health`

## 手动部署要点

```bash
sudo mkdir -p /opt/polycryindex
sudo cp -r Workspace /opt/polycryindex/
cd /opt/polycryindex
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r Workspace/backend/requirements.txt
cd Workspace/frontend
npm ci
APP_PROFILE=cloud VITE_APP_PROFILE=cloud npm run build
```

## 环境变量重点

| 配置项 | 说明 | Linux 部署默认值 |
|--------|------|------------------|
| `APP_PROFILE` | 主 profile 标识 | `cloud` |
| `APP_ENV` | 向后兼容环境标识 | `beta` |
| `SECRET_KEY` | JWT 签名密钥 | 自动生成 |
| `DEFAULT_ADMIN_PASSWORD` | 管理员初始密码 | 自动生成 |
| `FORTRAN_EXECUTABLE` | 主优化程序路径 | `/opt/polycryindex/Workspace/fortrancode/lm_opt2` |
| `FORTRAN_POSTPROCESS_EXECUTABLE` | 后处理程序路径 | `/opt/polycryindex/Workspace/fortrancode/lm_postprocess` |
| `ENABLE_DOCS` | 是否暴露 docs | `false` |
| `LOG_LEVEL` | 日志级别 | `warning` |

## systemd 路径

模板文件位于仓库：`Workspace/deploy/systemd/polycryindex.service`

关键路径：

- `WorkingDirectory=/opt/polycryindex/Workspace/backend`
- `ExecStart=/opt/polycryindex/venv/bin/python run_prod.py`
- `EnvironmentFile=/opt/polycryindex/Workspace/backend/.env`

## 健康检查与验证

```bash
curl -fsS http://127.0.0.1:8000/health
```

期望至少包含：

- `status=healthy`
- `profile=cloud`
- `app_env=beta`（或你显式传入的兼容值）

## 日志查看

```bash
journalctl -u polycryindex -f
journalctl -u polycryindex --since "1 hour ago"
```

## 常见问题排查

| 问题 | 排查方法 |
|------|---------|
| Fortran 找不到 | 检查 `Workspace/backend/.env` 中的 Fortran 路径 |
| 权限不足 | 检查 `/opt/polycryindex/Workspace/backend/` 与 `/opt/polycryindex/logs/` 权限 |
| 端口被占用 | `lsof -i :8000` |
| 前端 404 | 确认 `Workspace/frontend/dist/` 已构建 |
| 健康检查失败 | 先看 `curl http://127.0.0.1:8000/health`，再看 systemd / nohup 日志 |

## 磁盘清理

```bash
rm -rf /opt/polycryindex/Workspace/backend/temp/*
rm -rf /opt/polycryindex/Workspace/backend/userresult/*
```

## Cloud 验证清单

- [ ] 浏览器访问 `http://server-ip:8000` 加载前端
- [ ] 注册/登录/登出
- [ ] 上传数据文件
- [ ] 启动分析任务（Fortran 正常调用）
- [ ] 查看任务状态和日志
- [ ] 下载结果（zip / hdf5 / cell / miller）
- [ ] 峰提取功能（原始图像 + 积分图像）
- [ ] 管理员登录及后台全功能
- [ ] `/health` 返回 `profile=cloud`
- [ ] 服务重启后可正常恢复
- [ ] SPA 路由刷新不 404
