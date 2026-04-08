#!/usr/bin/env bash
set -euo pipefail

APP_INSTALL_DIR="${APP_INSTALL_DIR:-$HOME/.local/share/polycryindex}"
SERVICE_NAME="${SERVICE_NAME:-polycryindex}"
REMOVE_INSTALL_DIR="${REMOVE_INSTALL_DIR:-1}"

LOG_DIR="$APP_INSTALL_DIR/logs"
PID_FILE="$LOG_DIR/polycryindex.pid"
USER_SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
USER_UNIT_FILE="$USER_SYSTEMD_DIR/${SERVICE_NAME}.service"

log() {
  printf '\n[%s] %s\n' "$1" "$2"
}

info() {
  printf '[INFO] %s\n' "$1"
}

die() {
  printf '[ERROR] %s\n' "$1" >&2
  exit 1
}

stop_user_service() {
  log "1/4" "Stop user systemd service / 停止用户级 systemd 服务"
  if systemctl --user list-unit-files | grep -q "^${SERVICE_NAME}\.service"; then
    systemctl --user stop "$SERVICE_NAME" || true
    systemctl --user disable "$SERVICE_NAME" || true
  else
    info "User systemd unit ${SERVICE_NAME}.service not found / 未发现用户级服务 ${SERVICE_NAME}.service"
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

remove_user_unit() {
  log "3/4" "Remove user service binding / 删除用户级服务绑定"
  if [ -f "$USER_UNIT_FILE" ]; then
    rm -f "$USER_UNIT_FILE"
    systemctl --user daemon-reload || true
    systemctl --user reset-failed || true
  else
    info "User unit file already absent / 用户级服务文件已不存在"
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
  printf '\nUser uninstall completed / 用户卸载完成\n'
  printf 'Install dir / 安装目录: %s\n' "$APP_INSTALL_DIR"
  printf 'User service / 用户服务: %s\n' "$SERVICE_NAME"
  printf 'Removed install dir / 已删除安装目录: %s\n' "$( [ "$REMOVE_INSTALL_DIR" = "1" ] && printf 'yes' || printf 'no' )"
  printf 'Kept system packages / 保留系统包: yes\n'
  printf 'Kept global runtimes / 保留全局运行环境: yes\n'
}

main() {
  [ "$(uname -s)" = "Linux" ] || die "Linux only / 该脚本仅支持 Linux"
  [ "$(id -u)" -ne 0 ] || die "Do not run as root / 用户卸载脚本不要使用 root 或 sudo 运行"

  stop_user_service
  stop_standard_process
  remove_user_unit
  remove_install_dir
  print_summary
}

main "$@"
