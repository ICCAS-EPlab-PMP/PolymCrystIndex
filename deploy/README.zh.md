[English](README.md)

# PolyCryIndex 服务器部署指南

## 环境要求

| 依赖 | 最低版本 | 用途 |
|------|---------|------|
| 操作系统 | Rocky 9 / Ubuntu 20.04+ / CentOS 7+ / macOS 12+ | 运行环境 |
| Python | 3.9+ | 后端运行时 |
| Node.js | 16+ | 构建前端 |
| gfortran | 任意可用版本 | 编译 Fortran 优化程序 |
| curl | 任意可用版本 | 健康检查 |

---

## 安装目录结构

```text
/opt/polycryindex-pre/
├── Workspace/
│   ├── backend/
│   │   ├── .env                  ← 自动生成的配置（含密钥）
│   │   ├── run_prod.py           ← 后端入口
│   │   ├── users.db              ← 用户数据库（自动创建）
│   │   ├── temp/                 ← 用户上传文件
│   │   ├── result/               ← 分析结果
│   │   ├── hdf5/                 ← HDF5 数据
│   │   ├── userresult/           ← 用户自定义结果
│   │   ├── workdir/              ← 工作目录
│   │   └── figures/              ← 图表输出
│   ├── frontend/
│   │   └── dist/                 ← 构建后的前端
│   ├── fortrancode/
│   │   ├── lm_opt2               ← 主优化程序
│   │   └── lm_postprocess        ← 后处理程序
│   └── fiber_diffraction_indexing/
├── venv/                         ← Python 虚拟环境
└── logs/                         ← 运行日志
```

---

## 首次部署

### Linux（root 方式）

```bash
# 1. 获取源码
git clone https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex.git
cd PolymCrystalIndex/deploy/server

# 2. 一键部署（systemd 长期运行）
sudo APP_PROFILE=cloud DEPLOY_MODE=1 bash ./deploy_linux.sh

# 或普通方式（nohup，适合临时测试）
sudo APP_PROFILE=cloud DEPLOY_MODE=0 bash ./deploy_linux.sh
```

### Linux（当前用户方式）

不需要 root 权限，安装到 `$HOME/.local/share/polycryindex-pre/`：

```bash
cd deploy/server
APP_PROFILE=cloud DEPLOY_MODE=1 bash ./install_user_linux.sh
```

> 用户级 systemd 服务默认不会在退出登录后继续运行。如需持久运行：
> ```bash
> sudo loginctl enable-linger $USER
> ```

### macOS

> ⚠️ **注意：macOS 部署未经官方测试或验证。以下说明仅供参考，可能需要手动调整。**

macOS 不支持 systemd，需手动部署：

```bash
# 1. 安装依赖
brew install python node gfortran curl

# 2. 获取源码
git clone https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex.git
cd PolymCrystalIndex

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r fiber_diffraction_indexing/requirements.txt

# 4. 编译 Fortran
cd fortrancode
gfortran -O2 -o lm_opt2 minpack.f90 lm_opt2.f90
gfortran -O2 -o lm_postprocess out.f90
cd ..

# 5. 构建前端
cd frontend
npm ci
APP_PROFILE=cloud VITE_APP_PROFILE=cloud npm run build
cd ..

# 6. 创建运行目录
mkdir -p backend/{temp,result,hdf5,userresult,workdir,figures}

# 7. 生成配置文件
cat > backend/.env <<'EOF'
SECRET_KEY=$(openssl rand -hex 32)
DEFAULT_ADMIN_PASSWORD=$(python3 -c "import secrets; print(''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789') for _ in range(16)))")
FORTRAN_EXECUTABLE=$(pwd)/fortrancode/lm_opt2
FORTRAN_POSTPROCESS_EXECUTABLE=$(pwd)/fortrancode/lm_postprocess
APP_PROFILE=cloud
APP_ENV=production
HOST=127.0.0.1
PORT=8000
ENABLE_DOCS=false
LOG_LEVEL=warning
CORS_ORIGINS=["http://localhost:8000","http://127.0.0.1:8000"]
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_JOBS=1
OMP_NUM_THREADS=4
UPLOAD_DIR=$(pwd)/backend/temp
RESULT_DIR=$(pwd)/backend/result
HDF5_DIR=$(pwd)/backend/hdf5
USER_RESULT_DIR=$(pwd)/backend/userresult
WORKING_DIR=$(pwd)/backend/workdir
EOF

# 8. 启动服务
cd backend
nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## 更新（升级到新版本）

### 更新原则

- 更新代码时，**用户数据自动保留**（temp、result、hdf5、userresult、workdir、figures）
- **密钥和管理员密码自动保留**（不会被覆盖）
- 其他 `.env` 配置项会更新为新版默认值

### Linux 更新

```bash
# 1. 拉取最新代码
cd /path/to/PolymCrystalIndex
git pull

# 2. 重新运行部署脚本（会自动保留用户数据）
cd deploy/server
sudo APP_PROFILE=cloud DEPLOY_MODE=1 bash ./deploy_linux.sh

# 脚本会自动：
# - 同步新版代码（保留用户数据目录）
# - 保留已有的 SECRET_KEY 和管理员密码
# - 更新 Python 依赖
# - 重新编译 Fortran
# - 重新构建前端
# - 重启服务
```

### macOS 更新

> ⚠️ **注意：macOS 部署未经官方测试或验证。以下说明仅供参考，可能需要手动调整。**

```bash
# 1. 拉取最新代码
cd /path/to/PolymCrystalIndex
git pull

# 2. 停止旧服务
kill $(cat logs/polycryindex.pid)

# 3. 更新依赖
source venv/bin/activate
pip install -r backend/requirements.txt
pip install -r fiber_diffraction_indexing/requirements.txt

# 4. 重新编译 Fortran
cd fortrancode
gfortran -O2 -o lm_opt2 minpack.f90 lm_opt2.f90
gfortran -O2 -o lm_postprocess out.f90
cd ..

# 5. 重新构建前端
cd frontend
npm ci
APP_PROFILE=cloud VITE_APP_PROFILE=cloud npm run build
cd ..

# 6. 重启服务
cd backend
nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## 环境变量说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `APP_PROFILE` | 运行模式 | `cloud`（服务器） |
| `APP_ENV` | 环境标识 | `production` |
| `SECRET_KEY` | JWT 签名密钥 | 自动生成（更新时保留） |
| `DEFAULT_ADMIN_PASSWORD` | 管理员初始密码 | 自动生成（更新时保留） |
| `HOST` | 监听地址 | `0.0.0.0`（Linux）/ `127.0.0.1`（macOS） |
| `PORT` | 监听端口 | `8000` |
| `APP_HOST` | 服务器域名/IP（用于 CORS） | `0.0.0.0` |
| `FORTRAN_EXECUTABLE` | 主优化程序路径 | 自动设置 |
| `FORTRAN_POSTPROCESS_EXECUTABLE` | 后处理程序路径 | 自动设置 |
| `ENABLE_DOCS` | 是否暴露 API 文档 | `false` |
| `LOG_LEVEL` | 日志级别 | `warning` |
| `MAX_JOBS` | 最大并行任务数 | `1` |
| `OMP_NUM_THREADS` | OpenMP 线程数 | `4` |

---

## 服务管理

### systemd 方式（Linux）

```bash
# 查看状态
sudo systemctl status polycryindex-pre

# 查看日志
sudo journalctl -u polycryindex-pre -f
sudo journalctl -u polycryindex-pre --since "1 hour ago"

# 重启
sudo systemctl restart polycryindex-pre

# 停止
sudo systemctl stop polycryindex-pre
```

### nohup 方式（Linux / macOS）

```bash
# 查看日志
tail -f logs/polycryindex.out

# 停止
kill $(cat logs/polycryindex.pid)

# 重启
kill $(cat logs/polycryindex.pid)
cd backend && nohup ../venv/bin/python run_prod.py > ../logs/polycryindex.out 2>&1 &
echo $! > ../logs/polycryindex.pid
```

---

## 健康检查

```bash
curl -fsS http://127.0.0.1:8000/health
```

期望返回：
- `status=healthy`
- `profile=cloud`
- `app_env=production`

---

## 卸载

### Linux（root 方式）

```bash
cd deploy/server
sudo bash ./uninstall_linux.sh
```

默认会删除安装目录 `/opt/polycryindex-pre/`。如需保留数据：

```bash
sudo REMOVE_INSTALL_DIR=0 bash ./uninstall_linux.sh
```

### Linux（用户方式）

```bash
cd deploy/server
bash ./uninstall_user_linux.sh
```

### macOS

> ⚠️ **注意：macOS 部署未经官方测试或验证。以下说明仅供参考，可能需要手动调整。**

```bash
# 停止服务
kill $(cat logs/polycryindex.pid)

# 删除安装目录
rm -rf /path/to/PolymCrystalIndex
```

---

## 常见问题

| 问题 | 排查方法 |
|------|---------|
| Fortran 找不到 | 检查 `backend/.env` 中的 `FORTRAN_EXECUTABLE` 路径 |
| 权限不足 | 检查 `backend/` 和 `logs/` 目录权限 |
| 端口被占用 | `lsof -i :8000` 或 `ss -ltnp | grep :8000` |
| 前端 404 | 确认 `frontend/dist/` 已构建 |
| 健康检查失败 | 先 `curl http://127.0.0.1:8000/health`，再看日志 |
| CORS 错误 | 设置 `APP_HOST` 为服务器实际 IP 或域名 |
| 更新后密码变了 | 不应发生——脚本会自动保留已有密码 |

---

## 磁盘清理

```bash
# 清理临时上传文件
rm -rf /opt/polycryindex-pre/Workspace/backend/temp/*

# 清理用户结果（谨慎操作）
rm -rf /opt/polycryindex-pre/Workspace/backend/userresult/*
```

---

## 验证清单

- [ ] 浏览器访问 `http://server-ip:8000` 加载前端
- [ ] 注册 / 登录 / 登出正常
- [ ] 上传数据文件成功
- [ ] 启动分析任务（Fortran 正常调用）
- [ ] 查看任务状态和日志
- [ ] 下载结果（zip / hdf5 / cell / miller）
- [ ] 峰提取功能正常
- [ ] 管理员登录及后台功能正常
- [ ] `/health` 返回 `profile=cloud`
- [ ] 服务重启后自动恢复
- [ ] 浏览器刷新路由不 404
