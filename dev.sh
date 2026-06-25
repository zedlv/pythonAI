#!/usr/bin/env bash
# 一键管理 fastapi_demo 开发环境：Redis、PostgreSQL、FastAPI
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FASTAPI_DIR="${ROOT_DIR}/fastapi_demo"
VENV_ACTIVATE="${FASTAPI_DIR}/venv/bin/activate"

REDIS_SERVICE="redis"
POSTGRES_SERVICE="postgresql@16"
CACHE_KEY_PREFIX="chat:answer:"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}→${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*" >&2; }

brew_service_running() {
  local service="$1"
  brew services list 2>/dev/null | awk -v s="$service" '$1 == s && $2 == "started" { found=1 } END { exit !found }'
}

is_uvicorn_running() {
  pgrep -f "uvicorn main:app" >/dev/null 2>&1
}

pg_isready_cmd() {
  if command -v pg_isready &>/dev/null; then
    command pg_isready
  elif [[ -x /opt/homebrew/opt/postgresql@16/bin/pg_isready ]]; then
    /opt/homebrew/opt/postgresql@16/bin/pg_isready
  elif [[ -x /usr/local/opt/postgresql@16/bin/pg_isready ]]; then
    /usr/local/opt/postgresql@16/bin/pg_isready
  else
    return 127
  fi
}

start_redis() {
  if brew_service_running "$REDIS_SERVICE"; then
    ok "Redis 已在运行"
  else
    info "启动 Redis..."
    brew services start "$REDIS_SERVICE"
    ok "Redis 已启动（已设为开机自启）"
  fi
  if redis-cli ping &>/dev/null; then
    ok "Redis 连接正常: PONG"
  else
    fail "Redis 启动后仍无法连接"
    return 1
  fi
}

stop_redis() {
  if brew_service_running "$REDIS_SERVICE"; then
    info "停止 Redis..."
    brew services stop "$REDIS_SERVICE"
    ok "Redis 已停止"
  else
    warn "Redis 未在运行"
  fi
}

start_postgres() {
  if brew_service_running "$POSTGRES_SERVICE"; then
    ok "PostgreSQL 已在运行"
  else
    info "启动 PostgreSQL..."
    brew services start "$POSTGRES_SERVICE"
    ok "PostgreSQL 已启动（已设为开机自启）"
  fi
  if pg_isready_cmd -h 127.0.0.1 &>/dev/null; then
    ok "PostgreSQL 连接正常"
  else
    fail "PostgreSQL 启动后仍无法连接，请稍等几秒后重试"
    return 1
  fi
}

stop_postgres() {
  if brew_service_running "$POSTGRES_SERVICE"; then
    info "停止 PostgreSQL..."
    brew services stop "$POSTGRES_SERVICE"
    ok "PostgreSQL 已停止"
  else
    warn "PostgreSQL 未在运行"
  fi
}

run_api_foreground() {
  if [[ ! -f "$VENV_ACTIVATE" ]]; then
    fail "虚拟环境不存在: ${VENV_ACTIVATE}"
    fail "请先执行: cd fastapi_demo && python -m venv venv && pip install -r requirements.txt"
    return 1
  fi

  if is_uvicorn_running; then
    warn "FastAPI 已在运行，请先 stop api 或 Ctrl+C 停止后再启动"
    return 1
  fi

  info "启动 FastAPI（前台，按 Ctrl+C 停止）..."
  cd "$FASTAPI_DIR"
  # shellcheck disable=SC1091
  source venv/bin/activate
  exec python -m uvicorn main:app --reload
}

stop_api() {
  if is_uvicorn_running; then
    info "停止 FastAPI..."
    pkill -f "uvicorn main:app" 2>/dev/null || true
    ok "FastAPI 已停止"
  else
    warn "FastAPI 未在运行"
  fi
}

cmd_start() {
  local target="${1:-all}"
  case "$target" in
    all)
      start_redis
      start_postgres
      run_api_foreground
      ;;
    redis)       start_redis ;;
    postgres|pg) start_postgres ;;
    api)         run_api_foreground ;;
    *)
      fail "未知启动目标: $target"
      usage
      return 1
      ;;
  esac
}

cmd_stop() {
  local target="${1:-all}"
  case "$target" in
    all)
      stop_api
      stop_redis
      stop_postgres
      ;;
    redis)       stop_redis ;;
    postgres|pg) stop_postgres ;;
    api)         stop_api ;;
    *)
      fail "未知停止目标: $target"
      usage
      return 1
      ;;
  esac
}

cmd_status() {
  echo ""
  echo "========== 服务状态 =========="

  if brew_service_running "$REDIS_SERVICE"; then
    ok "Redis:        运行中"
    if redis-cli ping &>/dev/null; then
      echo "              redis-cli ping → PONG"
    else
      warn "              redis-cli ping → 无响应"
    fi
  else
    warn "Redis:        未运行  → 执行: $0 start redis"
  fi

  if brew_service_running "$POSTGRES_SERVICE"; then
    ok "PostgreSQL:   运行中"
    if pg_isready_cmd -h 127.0.0.1 &>/dev/null; then
      echo "              pg_isready → accepting connections"
    else
      warn "              pg_isready → 无响应"
    fi
  else
    warn "PostgreSQL:   未运行  → 执行: $0 start postgres"
  fi

  if is_uvicorn_running; then
    ok "FastAPI:      运行中 → http://127.0.0.1:8000"
  else
    warn "FastAPI:      未运行  → 执行: $0 start api"
  fi

  echo ""
  echo "brew services:"
  brew services list 2>/dev/null | grep -E "redis|postgres" || true
  echo ""
}

cmd_redis() {
  local sub="${1:-ping}"
  shift || true

  case "$sub" in
    ping)
      if redis-cli ping; then
        ok "Redis 连接正常"
      else
        fail "Redis 无法连接，请先执行: $0 start redis"
        return 1
      fi
      ;;
    keys)
      info "缓存键列表 (${CACHE_KEY_PREFIX}*)"
      redis-cli --scan --pattern "${CACHE_KEY_PREFIX}*"
      ;;
    get)
      local md5="${1:-}"
      if [[ -z "$md5" ]]; then
        fail "请提供 MD5 值，例如: $0 redis get a1b2c3d4..."
        return 1
      fi
      local key="${CACHE_KEY_PREFIX}${md5}"
      info "查询缓存: ${key}"
      local value
      value="$(redis-cli get "$key")"
      if [[ -z "$value" || "$value" == "(nil)" ]]; then
        warn "缓存不存在或已过期"
      else
        echo "$value"
      fi
      local ttl
      ttl="$(redis-cli ttl "$key")"
      echo "TTL: ${ttl}s"
      ;;
    count)
      local count
      count="$(redis-cli --scan --pattern "${CACHE_KEY_PREFIX}*" | wc -l | tr -d ' ')"
      ok "缓存条目数: ${count}"
      ;;
  esac
}

usage() {
  cat <<EOF

用法: $0 <命令> [参数]

启动 / 停止
  start [all|redis|postgres|api]   启动服务（默认 all：Redis + PostgreSQL + FastAPI 前台）
  stop  [all|redis|postgres|api]   停止服务（默认 all）
  status                           查看所有服务状态

Redis 缓存
  redis ping                       验证 Redis 连接
  redis keys                       列出所有 chat:answer:* 缓存键
  redis get <md5>                  按 MD5 查看单条缓存内容及 TTL
  redis count                      统计缓存条目数

示例
  $0 start                         # 启 Redis + PostgreSQL，再前台跑 FastAPI
  $0 start api                     # 仅前台启动 FastAPI（等同手动 cd + venv + uvicorn）
  $0 stop                          # 一键停止全部
  $0 status                        # 查看状态
  $0 redis keys
  $0 redis get d41d8cd98f00b204e9800998ecf8427e

EOF
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    start)       cmd_start "${1:-all}" ;;
    stop)        cmd_stop "${1:-all}" ;;
    status|st)   cmd_status ;;
    redis)       cmd_redis "$@" ;;
    help|-h|--help|"") usage ;;
    *)
      fail "未知命令: $cmd"
      usage
      return 1
      ;;
  esac
}

main "$@"
