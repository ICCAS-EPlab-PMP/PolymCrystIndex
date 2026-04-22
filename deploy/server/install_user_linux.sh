#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_INSTALL_DIR="${APP_INSTALL_DIR:-$HOME/.local/share/polycryindex}"
PROJECT_ROOT="$APP_INSTALL_DIR/Workspace"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
FORTRAN_DIR="$PROJECT_ROOT/fortrancode"
VENV_DIR="$APP_INSTALL_DIR/venv"
LOG_DIR="$APP_INSTALL_DIR/logs"
STD_LOG_FILE="$LOG_DIR/polycryindex.out"
PID_FILE="$LOG_DIR/polycryindex.pid"
SERVICE_NAME="${SERVICE_NAME:-polycryindex}"
USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
USER_UNIT_FILE="$USER_SYSTEMD_DIR/${SERVICE_NAME}.service"

SOURCE_BACKEND_DIR="$SOURCE_WORKSPACE_ROOT/backend"
SOURCE_FRONTEND_DIR="$SOURCE_WORKSPACE_ROOT/frontend"
SOURCE_FORTRAN_DIR="$SOURCE_WORKSPACE_ROOT/fortrancode"

APP_HOST="${APP_HOST:-127.0.0.1}"
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

generate_secret() {
  if has_command openssl; then
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

  log "2/10" "Sync Workspace source to user install root / 同步 Workspace 源码到用户安装目录"

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
  printf '  1 = User service deployment (systemctl --user) / 用户级长期部署\n'
  printf 'Enter 0 or 1 / 请输入 0 或 1: '
  read -r DEPLOY_MODE

  case "$DEPLOY_MODE" in
    0|1) ;;
    *) die "Invalid choice, expected 0 or 1 / 输入无效，只能是 0 或 1" ;;
  esac
}

ensure_commands() {
  log "1/10" "Check required commands / 检查关键命令"
  has_command python3 || die "python3 is not available / python3 不可用"
  has_command npm || die "npm is not available / npm 不可用"
  has_command gfortran || die "gfortran is not available / gfortran 不可用"
  has_command curl || die "curl is not available / curl 不可用"

  if [ "$DEPLOY_MODE" = "1" ]; then
    has_command systemctl || die "systemctl is required for user service deployment / 用户级长期部署需要 systemctl"
  fi
}

prepare_directories() {
  log "3/10" "Create runtime directories / 创建运行目录"
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
  log "4/10" "Setup Python virtual environment / 配置 Python 虚拟环境"
  if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
  fi

  # Rocky 9 / RHEL 9 的 python3 -m venv 不带 ensurepip，venv 里没有 pip
  if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    info "pip not found in venv, bootstrapping... / venv 中未检测到 pip，正在引导安装"
    if has_command curl; then
      curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    elif has_command wget; then
      wget -qO /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
    else
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
  log "5/10" "Build frontend / 构建前端"
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
  log "6/10" "Compile Fortran binaries / 编译 Fortran 程序"
  pushd "$FORTRAN_DIR" >/dev/null
  gfortran -O2 -fopenmp -o lm_opt2 minpack.f90 lm_opt2.f90
  gfortran -O2 -o lm_postprocess out.f90
  chmod +x lm_opt2 lm_postprocess
  popd >/dev/null
}

write_env_file() {
  log "7/10" "Generate backend env file / 生成后端环境文件"

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
HOST=$APP_HOST
PORT=$APP_PORT
ENABLE_DOCS=false
LOG_LEVEL=warning
CORS_ORIGINS=["http://$APP_HOST:$APP_PORT","http://localhost:$APP_PORT"]
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_JOBS=1
OMP_NUM_THREADS=4
UPLOAD_DIR=$BACKEND_DIR/temp
RESULT_DIR=$BACKEND_DIR/result
HDF5_DIR=$BACKEND_DIR/hdf5
USER_RESULT_DIR=$BACKEND_DIR/userresult
WORKING_DIR=$BACKEND_DIR/workdir
EOF

  chmod 600 "$BACKEND_DIR/.env"
}

stop_standard_process() {
  if [ -f "$PID_FILE" ]; then
    local old_pid
    old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid" || true
      sleep 1
    fi
    rm -f "$PID_FILE"
  fi

  pkill -f "$VENV_DIR/bin/python run_prod.py" >/dev/null 2>&1 || true
}

start_standard_deploy() {
  log "8/10" "Start app with nohup / 使用 nohup 启动服务"
  stop_standard_process
  pushd "$BACKEND_DIR" >/dev/null
  nohup "$VENV_DIR/bin/python" run_prod.py > "$STD_LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  popd >/dev/null
}

install_user_systemd_service() {
  log "8/10" "Install user systemd service / 安装用户级 systemd 服务"
  mkdir -p "$USER_SYSTEMD_DIR"

  cat > "$USER_UNIT_FILE" <<EOF
[Unit]
Description=PolyCryIndex API Server (User)
After=default.target

[Service]
Type=simple
WorkingDirectory=$BACKEND_DIR
EnvironmentFile=$BACKEND_DIR/.env
ExecStart=$VENV_DIR/bin/python run_prod.py
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=default.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable "$SERVICE_NAME"
  systemctl --user restart "$SERVICE_NAME"
}

print_failure_diagnostics() {
  warn "Deployment health check failed. Collecting diagnostics... / 健康检查失败，正在收集诊断信息..."
  printf '\n[DIAG] Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf '[DIAG] Workspace dir / Workspace 目录: %s\n' "$PROJECT_ROOT"
  printf '[DIAG] Backend env / 环境文件: %s\n' "$BACKEND_DIR/.env"
  printf '[DIAG] Health URL / 健康检查地址: http://%s:%s/health\n' "$APP_HOST" "$APP_PORT"

  if [ "$DEPLOY_MODE" = "1" ]; then
    printf '[DIAG] User service / 用户服务: %s\n' "$SERVICE_NAME"
    systemctl --user status "$SERVICE_NAME" --no-pager || true
    journalctl --user -u "$SERVICE_NAME" -n 80 --no-pager || true
  else
    printf '[DIAG] PID file / PID 文件: %s\n' "$PID_FILE"
    if [ -f "$PID_FILE" ]; then
      printf '[DIAG] PID / 进程号: %s\n' "$(cat "$PID_FILE" 2>/dev/null || true)"
    fi
    if [ -f "$STD_LOG_FILE" ]; then
      printf '\n[DIAG] Last log lines / 最近日志:\n'
      tail -n 80 "$STD_LOG_FILE" || true
    fi
  fi

  printf '\n[DIAG] Port check / 端口检查:\n'
  if has_command ss; then
    ss -ltnp | grep ":$APP_PORT" || true
  fi
}

health_check() {
  local url="http://$APP_HOST:$APP_PORT/health"
  local attempt

  log "9/10" "Run health check / 执行健康检查"
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
  log "10/10" "Deployment summary / 部署摘要"
  printf 'Mode / 模式: %s\n' "$( [ "$DEPLOY_MODE" = "1" ] && printf 'user-systemd' || printf 'standard(nohup)' )"
  printf 'Source workspace / 源码 Workspace: %s\n' "$SOURCE_WORKSPACE_ROOT"
  printf 'Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf 'Workspace dir / Workspace 目录: %s\n' "$PROJECT_ROOT"
  printf 'Web URL / 访问地址: http://%s:%s\n' "$APP_HOST" "$APP_PORT"
  printf 'Health URL / 健康检查: http://%s:%s/health\n' "$APP_HOST" "$APP_PORT"
  printf 'Admin username / 管理员账号: admin\n'
  printf 'Admin password / 管理员密码: %s\n' "$ADMIN_PASSWORD_VALUE"

  if [ "$DEPLOY_MODE" = "1" ]; then
    printf 'User service / 用户服务: %s\n' "$SERVICE_NAME"
    printf 'Status / 状态: systemctl --user status %s --no-pager\n' "$SERVICE_NAME"
    printf 'Logs / 日志: journalctl --user -u %s -f\n' "$SERVICE_NAME"
    printf 'Linger note / 持久运行提示: use sudo loginctl enable-linger %s if you want the service to survive logout\n' "$USER"
  else
    printf 'PID file / PID 文件: %s\n' "$PID_FILE"
    printf 'Log file / 日志文件: %s\n' "$STD_LOG_FILE"
  fi
}

main() {
  [ "$(uname -s)" = "Linux" ] || die "Linux only / 该脚本仅支持 Linux"
  [ "$(id -u)" -ne 0 ] || die "Do not run as root / 用户安装脚本不要使用 root 或 sudo 运行"

  need_file "$SOURCE_BACKEND_DIR"
  need_file "$SOURCE_FRONTEND_DIR"
  need_file "$SOURCE_FORTRAN_DIR"
  need_file "$SOURCE_BACKEND_DIR/requirements.txt"
  need_file "$SOURCE_FRONTEND_DIR/package.json"
  need_file "$SOURCE_FORTRAN_DIR/lm_opt2.f90"
  need_file "$SOURCE_FORTRAN_DIR/out.f90"
  need_file "$SOURCE_FORTRAN_DIR/minpack.f90"

  prompt_deploy_mode
  ensure_commands
  sync_project_files
  prepare_directories
  setup_python_env
  build_frontend
  build_fortran
  write_env_file

  if [ "$DEPLOY_MODE" = "1" ]; then
    install_user_systemd_service
  else
    start_standard_deploy
  fi

  health_check
  print_summary
}

main "$@"
