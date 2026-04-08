#!/usr/bin/env bash
set -euo pipefail

APP_INSTALL_DIR="${APP_INSTALL_DIR:-/opt/polycryindex}"
SERVICE_NAME="${SERVICE_NAME:-polycryindex}"
REMOVE_INSTALL_DIR="${REMOVE_INSTALL_DIR:-1}"

BACKEND_DIR="$APP_INSTALL_DIR/backend"
LOG_DIR="$APP_INSTALL_DIR/logs"
PID_FILE="$LOG_DIR/polycryindex.pid"
SYSTEMD_UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

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

stop_systemd_service() {
  if command -v systemctl >/dev/null 2>&1; then
    if systemctl list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
      log "1/4" "Stop and disable systemd service / 停止并禁用 systemd 服务"
      systemctl stop "$SERVICE_NAME" || true
      systemctl disable "$SERVICE_NAME" || true
    else
      info "Systemd unit ${SERVICE_NAME}.service not found / 未发现 systemd 服务 ${SERVICE_NAME}.service"
    fi
  else
    warn "systemctl not available, skip service stop / 未检测到 systemctl，跳过服务停止"
  fi
}

stop_standard_process() {
  log "2/4" "Stop standard-mode process / 停止普通模式进程"
  if [ -f "$PID_FILE" ]; then
    local old_pid
    old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$old_pid" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
      kill "$old_pid" || true
      sleep 1
    fi
    rm -f "$PID_FILE"
  fi

  pkill -f "$APP_INSTALL_DIR/venv/bin/python run_prod.py" >/dev/null 2>&1 || true
}

remove_systemd_unit() {
  log "3/4" "Remove systemd unit binding / 删除 systemd 绑定"
  if [ -f "$SYSTEMD_UNIT_FILE" ]; then
    rm -f "$SYSTEMD_UNIT_FILE"
    systemctl daemon-reload || true
    systemctl reset-failed || true
  else
    info "Systemd unit file already absent / systemd 服务文件已不存在"
  fi
}

remove_install_dir() {
  log "4/4" "Remove installed project files / 删除已安装项目文件"
  if [ "$REMOVE_INSTALL_DIR" != "1" ]; then
    info "REMOVE_INSTALL_DIR=$REMOVE_INSTALL_DIR, keep install directory / 保留安装目录"
    return
  fi

  if [ -d "$APP_INSTALL_DIR" ]; then
    rm -rf "$APP_INSTALL_DIR"
    info "Removed install directory: $APP_INSTALL_DIR / 已删除安装目录: $APP_INSTALL_DIR"
  else
    info "Install directory not found: $APP_INSTALL_DIR / 安装目录不存在: $APP_INSTALL_DIR"
  fi
}

print_summary() {
  printf '\nUninstall completed / 卸载完成\n'
  printf 'Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf 'Service / 服务: %s\n' "$SERVICE_NAME"
  printf 'Removed install dir / 已删除安装目录: %s\n' "$( [ "$REMOVE_INSTALL_DIR" = "1" ] && printf 'yes' || printf 'no' )"
  printf 'Kept system packages / 保留系统包: yes\n'
  printf 'Kept global runtimes / 保留全局运行环境: yes\n'
  printf 'Kept service user / 保留服务用户: yes\n'
}

main() {
  [ "$(uname -s)" = "Linux" ] || die "Linux only / 该脚本仅支持 Linux"
  [ "$(id -u)" -eq 0 ] || die "Run as root or with sudo / 请使用 root 或 sudo 运行"

  stop_systemd_service
  stop_standard_process
  remove_systemd_unit
  remove_install_dir
  print_summary
}

main "$@"
