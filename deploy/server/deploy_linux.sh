#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/polycryindex}"
PROJECT_ROOT="$APP_INSTALL_DIR/Workspace"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
FORTRAN_DIR="$PROJECT_ROOT/fortrancode"
VENV_DIR="$APP_INSTALL_DIR/venv"
LOG_DIR="$APP_INSTALL_DIR/logs"
STD_LOG_FILE="$LOG_DIR/polycryindex.out"
PID_FILE="$LOG_DIR/polycryindex.pid"
SERVICE_NAME="polycryindex"

SOURCE_BACKEND_DIR="$SOURCE_WORKSPACE_ROOT/backend"
SOURCE_FRONTEND_DIR="$SOURCE_WORKSPACE_ROOT/frontend"
SOURCE_FORTRAN_DIR="$SOURCE_WORKSPACE_ROOT/fortrancode"

APP_USER="${APP_USER:-polycryindex}"
APP_PORT="${APP_PORT:-8000}"
APP_PROFILE_VALUE="cloud"
APP_ENV_VALUE="${APP_ENV:-beta}"
SECRET_KEY_VALUE="${SECRET_KEY:-}"
ADMIN_PASSWORD_VALUE="${ADMIN_PASSWORD:-}"
DEPLOY_MODE="${DEPLOY_MODE:-}"

log() {
  printf '\n[%s] %s\n' "$1" "$2"
}

info() {
  printf '[INFO] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1" >&2
}

die() {
  printf '[ERROR] %s\n' "$1" >&2
  exit 1
}

need_file() {
  local path="$1"
  [ -e "$path" ] || die "Missing required file or directory / 缺少必需文件或目录: $path"
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
    return
  fi

  python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
}

generate_password() {
  python3 - <<'PY'
import secrets
alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
print("".join(secrets.choice(alphabet) for _ in range(16)))
PY
}

detect_pkg_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
  elif command -v dnf >/dev/null 2>&1; then
    echo "dnf"
  elif command -v yum >/dev/null 2>&1; then
    echo "yum"
  else
    die "No supported package manager found / 未找到支持的包管理器 (apt/dnf/yum)"
  fi
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

retry_command() {
  local attempts="$1"
  shift
  local delay=3
  local i

  for ((i = 1; i <= attempts; i++)); do
    if "$@"; then
      return 0
    fi
    if [ "$i" -lt "$attempts" ]; then
      warn "Command failed (attempt $i/$attempts), retrying in ${delay}s / 命令执行失败（第 $i/$attempts 次），${delay}s 后重试"
      sleep "$delay"
    fi
  done

  return 1
}

append_pkg_if_missing() {
  local cmd_name="$1"
  local pkg_name="$2"
  local array_name="$3"

  if ! has_command "$cmd_name"; then
    eval "$array_name+=(\"$pkg_name\")"
  else
    info "Skip $pkg_name, command '$cmd_name' already exists / 跳过 $pkg_name，检测到已有命令 '$cmd_name'"
  fi
}

sync_project_files() {
  local source_resolved
  local target_parent
  local target_resolved=""

  source_resolved="$(cd "$SOURCE_WORKSPACE_ROOT" && pwd)"
  target_parent="$(dirname "$PROJECT_ROOT")"
  mkdir -p "$target_parent"

  if [ -d "$PROJECT_ROOT" ]; then
    target_resolved="$(cd "$PROJECT_ROOT" && pwd)"
  fi

  log "3/11" "Sync Workspace source to install root / 同步 Workspace 源码到安装目录"

  if [ -n "$target_resolved" ] && [ "$source_resolved" = "$target_resolved" ]; then
    info "Source already matches install root / 当前源码目录已是安装目录"
    return
  fi

  mkdir -p "$PROJECT_ROOT"
  find "$PROJECT_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

  if has_command rsync; then
    rsync -a --delete \
      --exclude '.git' \
      --exclude 'venv' \
      --exclude 'logs' \
      --exclude 'backend/.env' \
      --exclude 'backend/users.db' \
      --exclude 'backend/temp' \
      --exclude 'backend/result' \
      --exclude 'backend/hdf5' \
      --exclude 'backend/userresult' \
      --exclude 'backend/workdir' \
      --exclude 'backend/figures' \
      --exclude 'frontend/dist' \
      "$SOURCE_WORKSPACE_ROOT/" "$PROJECT_ROOT/"
  else
    tar \
      --exclude='.git' \
      --exclude='venv' \
      --exclude='logs' \
      --exclude='backend/.env' \
      --exclude='backend/users.db' \
      --exclude='backend/temp' \
      --exclude='backend/result' \
      --exclude='backend/hdf5' \
      --exclude='backend/userresult' \
      --exclude='backend/workdir' \
      --exclude='backend/figures' \
      --exclude='frontend/dist' \
      -C "$SOURCE_WORKSPACE_ROOT" -cf - . | tar -C "$PROJECT_ROOT" -xf -
  fi
}

prompt_deploy_mode() {
  if [ -n "$DEPLOY_MODE" ]; then
    case "$DEPLOY_MODE" in
      0|1) return ;;
      *) die "DEPLOY_MODE must be 0 or 1 / DEPLOY_MODE 必须是 0 或 1" ;;
    esac
  fi

  printf '\nSelect deployment mode / 请选择部署模式:\n'
  printf '  0 = Standard deployment (nohup) / 普通部署（nohup）\n'
  printf '  1 = Long-term deployment (systemd) / 长期部署（systemd）\n'
  printf 'Enter 0 or 1 / 请输入 0 或 1: '
  read -r DEPLOY_MODE

  case "$DEPLOY_MODE" in
    0|1) ;;
    *) die "Invalid choice, expected 0 or 1 / 输入无效，只能是 0 或 1" ;;
  esac
}

install_system_packages() {
  local pkg_manager
  pkg_manager="$(detect_pkg_manager)"

  log "1/11" "Install system packages / 安装系统依赖"
  case "$pkg_manager" in
    apt)
      local packages=()
      export DEBIAN_FRONTEND=noninteractive
      apt-get update

      append_pkg_if_missing python3 python3 packages
      append_pkg_if_missing pip3 python3-pip packages
      append_pkg_if_missing gfortran gfortran packages
      append_pkg_if_missing curl curl packages

      if ! dpkg -s ca-certificates >/dev/null 2>&1; then
        packages+=(ca-certificates)
      else
        info "Skip ca-certificates, already installed / 跳过 ca-certificates，已安装"
      fi

      if ! has_command node || ! has_command npm; then
        packages+=(nodejs npm)
        info "Node.js/npm missing, will install from apt / 缺少 Node.js/npm，将通过 apt 安装"
      else
        info "Skip nodejs/npm, existing Node.js environment detected / 跳过 nodejs/npm，检测到现有 Node.js 环境"
      fi

      if [ "${#packages[@]}" -gt 0 ]; then
        apt-get install -y "${packages[@]}"
      else
        info "All required system packages already available / 系统依赖已存在，跳过安装"
      fi
      ;;
    dnf)
      local packages=()

      append_pkg_if_missing python3 python3 packages
      append_pkg_if_missing pip3 python3-pip packages
      append_pkg_if_missing gfortran gcc-gfortran packages
      append_pkg_if_missing curl curl packages

      if ! rpm -q ca-certificates >/dev/null 2>&1; then
        packages+=(ca-certificates)
      else
        info "Skip ca-certificates, already installed / 跳过 ca-certificates，已安装"
      fi

      if ! has_command node || ! has_command npm; then
        packages+=(nodejs)
        info "Node.js/npm missing, will try to install nodejs only / 缺少 Node.js/npm，将仅尝试安装 nodejs"
      else
        info "Skip nodejs/npm, existing Node.js environment detected / 跳过 nodejs/npm，检测到现有 Node.js 环境"
      fi

      if [ "${#packages[@]}" -gt 0 ]; then
        dnf install -y "${packages[@]}"
      else
        info "All required system packages already available / 系统依赖已存在，跳过安装"
      fi
      ;;
    yum)
      local packages=()

      append_pkg_if_missing python3 python3 packages
      append_pkg_if_missing pip3 python3-pip packages
      append_pkg_if_missing gfortran gcc-gfortran packages
      append_pkg_if_missing curl curl packages

      if ! rpm -q ca-certificates >/dev/null 2>&1; then
        packages+=(ca-certificates)
      else
        info "Skip ca-certificates, already installed / 跳过 ca-certificates，已安装"
      fi

      if ! has_command node || ! has_command npm; then
        packages+=(nodejs)
        info "Node.js/npm missing, will try to install nodejs only / 缺少 Node.js/npm，将仅尝试安装 nodejs"
      else
        info "Skip nodejs/npm, existing Node.js environment detected / 跳过 nodejs/npm，检测到现有 Node.js 环境"
      fi

      if [ "${#packages[@]}" -gt 0 ]; then
        yum install -y "${packages[@]}"
      else
        info "All required system packages already available / 系统依赖已存在，跳过安装"
      fi
      ;;
  esac
}

ensure_commands() {
  log "2/11" "Check required commands / 检查关键命令"
  command -v python3 >/dev/null 2>&1 || die "python3 is not available / python3 不可用"
  command -v npm >/dev/null 2>&1 || die "npm is not available / npm 不可用"
  command -v gfortran >/dev/null 2>&1 || die "gfortran is not available / gfortran 不可用"
  command -v curl >/dev/null 2>&1 || die "curl is not available / curl 不可用"

  if [ "$DEPLOY_MODE" = "1" ]; then
    command -v systemctl >/dev/null 2>&1 || die "systemctl is required for long-term deployment / 长期部署需要 systemctl"
  fi
}

ensure_user() {
  if [ "$DEPLOY_MODE" != "1" ]; then
    return
  fi

  log "4/11" "Prepare service user / 准备服务用户"
  if id "$APP_USER" >/dev/null 2>&1; then
    return
  fi

  local shell_path="/usr/sbin/nologin"
  [ -x "$shell_path" ] || shell_path="/sbin/nologin"
  useradd --system --create-home --shell "$shell_path" "$APP_USER"
}

prepare_directories() {
  log "5/11" "Create runtime directories / 创建运行目录"
  mkdir -p \
    "$BACKEND_DIR/temp" \
    "$BACKEND_DIR/result" \
    "$BACKEND_DIR/hdf5" \
    "$BACKEND_DIR/userresult" \
    "$BACKEND_DIR/workdir" \
    "$BACKEND_DIR/figures" \
    "$LOG_DIR"
}

setup_python_env() {
  log "6/11" "Setup Python virtual environment / 配置 Python 虚拟环境"
  if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
  fi

  # Rocky 9 / RHEL 9 的 python3 -m venv 不带 ensurepip，venv 里没有 pip
  # 兜底：检测不到 pip 就用 get-pip.py 或系统 pip 手动装进去
  if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    info "pip not found in venv, bootstrapping... / venv 中未检测到 pip，正在引导安装"
    if has_command curl; then
      curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    elif has_command wget; then
      wget -qO /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
    else
      # 最后手段：复制系统 pip（不推荐但比直接失败好）
      "$VENV_DIR/bin/python" -c "import ensurepip; ensurepip._main()" 2>/dev/null || \
        die "Cannot bootstrap pip in venv. Install curl or wget first / 无法引导 pip，请先安装 curl 或 wget"
    fi
    if [ -f /tmp/get-pip.py ]; then
      "$VENV_DIR/bin/python" /tmp/get-pip.py
      rm -f /tmp/get-pip.py
    fi
  fi

  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

  if [ -f "$PROJECT_ROOT/fiber_diffraction_indexing/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_ROOT/fiber_diffraction_indexing/requirements.txt"
  fi
}

build_frontend() {
  log "7/11" "Build frontend / 构建前端"
  pushd "$FRONTEND_DIR" >/dev/null
  if [ -f package-lock.json ]; then
    retry_command 3 npm ci --no-audit --fetch-retries=5 --fetch-retry-mintimeout=2000 --fetch-retry-maxtimeout=120000 || \
      die "npm ci failed after retries / npm ci 多次重试后仍失败"
  else
    retry_command 3 npm install --no-audit --fetch-retries=5 --fetch-retry-mintimeout=2000 --fetch-retry-maxtimeout=120000 || \
      die "npm install failed after retries / npm install 多次重试后仍失败"
  fi
  APP_PROFILE="$APP_PROFILE_VALUE" VITE_APP_PROFILE="$APP_PROFILE_VALUE" npm run build
  popd >/dev/null
}

build_fortran() {
  log "8/11" "Compile Fortran binaries / 编译 Fortran 程序"
  pushd "$FORTRAN_DIR" >/dev/null
  gfortran -O2 -fopenmp -o lm_opt2 minpack.f90 lm_opt2.f90
  gfortran -O2 -o lm_postprocess out.f90
  chmod +x lm_opt2 lm_postprocess
  popd >/dev/null
}

write_env_file() {
  log "9/11" "Generate backend env file / 生成后端环境文件"

  if [ -z "$SECRET_KEY_VALUE" ]; then
    SECRET_KEY_VALUE="$(generate_secret)"
  fi

  if [ -z "$ADMIN_PASSWORD_VALUE" ]; then
    ADMIN_PASSWORD_VALUE="$(generate_password)"
  fi

  cat > "$BACKEND_DIR/.env" <<EOF
SECRET_KEY=$SECRET_KEY_VALUE
DEFAULT_ADMIN_PASSWORD=$ADMIN_PASSWORD_VALUE
FORTRAN_EXECUTABLE=$FORTRAN_DIR/lm_opt2
FORTRAN_POSTPROCESS_EXECUTABLE=$FORTRAN_DIR/lm_postprocess
APP_PROFILE=$APP_PROFILE_VALUE
APP_ENV=$APP_ENV_VALUE
HOST=0.0.0.0
PORT=$APP_PORT
ENABLE_DOCS=false
LOG_LEVEL=warning
CORS_ORIGINS=["http://localhost:$APP_PORT","http://127.0.0.1:$APP_PORT"]
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_JOBS=1
OMP_NUM_THREADS=4
UPLOAD_DIR=$BACKEND_DIR/temp
RESULT_DIR=$BACKEND_DIR/result
HDF5_DIR=$BACKEND_DIR/hdf5
USER_RESULT_DIR=$BACKEND_DIR/userresult
WORKING_DIR=$BACKEND_DIR/workdir
EOF

  chmod 640 "$BACKEND_DIR/.env"
}

stop_standard_process() {
  if [ -f "$PID_FILE" ]; then
    local old_pid
    old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid"
      sleep 1
    fi
    rm -f "$PID_FILE"
  fi
}

start_standard_deploy() {
  log "10/11" "Start app with nohup / 使用 nohup 启动服务"
  stop_standard_process
  pushd "$BACKEND_DIR" >/dev/null
  nohup "$VENV_DIR/bin/python" run_prod.py > "$STD_LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  popd >/dev/null
}

print_failure_diagnostics() {
  warn "Deployment health check failed. Collecting diagnostics... / 健康检查失败，正在收集诊断信息..."
  printf '\n[DIAG] Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf '[DIAG] Workspace dir / Workspace 目录: %s\n' "$PROJECT_ROOT"
  printf '[DIAG] Backend env / 环境文件: %s\n' "$BACKEND_DIR/.env"
  printf '[DIAG] Health URL / 健康检查地址: http://127.0.0.1:%s/health\n' "$APP_PORT"

  if [ "$DEPLOY_MODE" = "1" ]; then
    printf '[DIAG] Service / 服务: %s\n' "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME" --no-pager || true
    journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  else
    printf '[DIAG] PID file / PID 文件: %s\n' "$PID_FILE"
    if [ -f "$PID_FILE" ]; then
      printf '[DIAG] PID / 进程号: %s\n' "$(cat "$PID_FILE" 2>/dev/null || true)"
    fi
    if [ -f "$STD_LOG_FILE" ]; then
      printf '\n[DIAG] Last log lines / 最近日志:\n'
      tail -n 80 "$STD_LOG_FILE" || true
    else
      warn "Log file not found / 日志文件不存在: $STD_LOG_FILE"
    fi
  fi

  printf '\n[DIAG] Port check / 端口检查:\n'
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp | grep ":$APP_PORT" || true
  fi
}

install_systemd_service() {
  log "10/11" "Install systemd service / 安装 systemd 服务"

  cat > "/etc/systemd/system/$SERVICE_NAME.service" <<EOF
[Unit]
Description=PolyCryIndex API Server
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/python run_prod.py
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

  chown -R "$APP_USER:$APP_USER" "$PROJECT_ROOT"
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
}

health_check() {
  local url="http://127.0.0.1:$APP_PORT/health"
  local attempt

  log "11/11" "Run health check / 执行健康检查"
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  print_failure_diagnostics
  die "Health check did not pass in time / 健康检查未在预期时间内通过: $url"
}

print_summary() {
  printf '\nDeployment completed / 部署完成\n'
  printf 'Mode / 模式: %s\n' "$( [ "$DEPLOY_MODE" = "1" ] && printf 'long-term(systemd)' || printf 'standard(nohup)' )"
  printf 'Source workspace / 源码 Workspace: %s\n' "$SOURCE_WORKSPACE_ROOT"
  printf 'Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf 'Workspace dir / Workspace 目录: %s\n' "$PROJECT_ROOT"
  printf 'Web URL / 访问地址: http://server-ip:%s\n' "$APP_PORT"
  printf 'Health URL / 健康检查: http://127.0.0.1:%s/health\n' "$APP_PORT"
  printf 'Admin username / 管理员账号: admin\n'
  printf 'Admin password / 管理员密码: %s\n' "$ADMIN_PASSWORD_VALUE"

  if [ "$DEPLOY_MODE" = "1" ]; then
    printf 'Service / 服务: %s\n' "$SERVICE_NAME"
    printf 'Status / 状态: systemctl status %s --no-pager\n' "$SERVICE_NAME"
    printf 'Logs / 日志: journalctl -u %s -f\n' "$SERVICE_NAME"
  else
    printf 'PID file / PID 文件: %s\n' "$PID_FILE"
    printf 'Log file / 日志文件: %s\n' "$STD_LOG_FILE"
    printf 'Stop command / 停止命令: kill $(cat %s)\n' "$PID_FILE"
  fi
}

main() {
  [ "$(uname -s)" = "Linux" ] || die "Linux only / 该脚本仅支持 Linux"
  [ "$(id -u)" -eq 0 ] || die "Run as root or with sudo / 请使用 root 或 sudo 运行"

  need_file "$SOURCE_BACKEND_DIR"
  need_file "$SOURCE_FRONTEND_DIR"
  need_file "$SOURCE_FORTRAN_DIR"
  need_file "$SOURCE_BACKEND_DIR/requirements.txt"
  need_file "$SOURCE_FRONTEND_DIR/package.json"
  need_file "$SOURCE_FORTRAN_DIR/lm_opt2.f90"
  need_file "$SOURCE_FORTRAN_DIR/out.f90"
  need_file "$SOURCE_FORTRAN_DIR/minpack.f90"

  prompt_deploy_mode
  install_system_packages
  ensure_commands
  sync_project_files
  ensure_user
  prepare_directories
  setup_python_env
  build_frontend
  build_fortran
  write_env_file

  if [ "$DEPLOY_MODE" = "1" ]; then
    install_systemd_service
  else
    start_standard_deploy
  fi

  health_check
  print_summary
}

main "$@"
