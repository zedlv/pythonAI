#!/usr/bin/env bash
# chat-api 冒烟测试：10+ 条 curl 自动化回归
# 用法：
#   cd fastapi_demo && ./scripts/smoke_test.sh
#   BASE_URL=http://127.0.0.1:8000 API_TOKEN=xxx ./scripts/smoke_test.sh
#   SKIP_LLM=1 ./scripts/smoke_test.sh   # 跳过依赖真实 LLM 的用例

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_TOKEN="${API_TOKEN:-mytoken123456}"
SKIP_LLM="${SKIP_LLM:-0}"

USER_ID="smoke_user"
SESSION_ID="sess_smoke_d27"
UNIQUE_MSG="smoke_cache_$(date +%s)"

PASS=0
FAIL=0
SKIP=0
CHAT_FIRST_OK=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

HTTP_CODE=""
HTTP_BODY=""

request() {
  local method="$1"
  local path="$2"
  shift 2

  local tmp
  tmp="$(mktemp)"
  if ! HTTP_CODE="$(
    curl -sS -o "${tmp}" -w "%{http_code}" \
      -X "${method}" \
      "${BASE_URL}${path}" \
      "$@"
  )"; then
    HTTP_CODE="000"
  fi
  HTTP_BODY="$(cat "${tmp}")"
  rm -f "${tmp}"
}

json_get() {
  local body="$1"
  local expr="$2"
  python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    sys.exit(1)
expr = sys.argv[2]
try:
    ok = bool(eval(expr, {'data': data}))
except Exception:
    ok = False
sys.exit(0 if ok else 1)
" "${body}" "${expr}"
}

pass_case() {
  echo -e "  ${GREEN}PASS${NC} $1"
  PASS=$((PASS + 1))
}

fail_case() {
  echo -e "  ${RED}FAIL${NC} $1"
  [[ -n "${2:-}" ]] && echo "        ${2}"
  FAIL=$((FAIL + 1))
}

skip_case() {
  echo -e "  ${YELLOW}SKIP${NC} $1"
  [[ -n "${2:-}" ]] && echo "        ${2}"
  SKIP=$((SKIP + 1))
}

chat_json() {
  local message="$1"
  python3 -c 'import json,sys; print(json.dumps({"user_id":sys.argv[1],"session_id":sys.argv[2],"message":sys.argv[3]}))' \
    "${USER_ID}" "${SESSION_ID}" "${message}"
}

echo "========================================"
echo " chat-api smoke test"
echo " BASE_URL=${BASE_URL}"
echo "========================================"

if ! curl -sS -o /dev/null --connect-timeout 2 "${BASE_URL}/ping" 2>/dev/null; then
  echo -e "${RED}ERROR${NC}: 无法连接 ${BASE_URL}，请先启动服务："
  echo "  docker compose up -d   # 或 uvicorn main:app --reload"
  exit 1
fi

# 1. /ping
request GET "/ping"
if [[ "${HTTP_CODE}" == "200" ]] && json_get "${HTTP_BODY}" "data.get('ok') is True"; then
  pass_case "GET /ping 返回 ok"
else
  fail_case "GET /ping 返回 ok" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 2. /healthz
request GET "/healthz"
if [[ "${HTTP_CODE}" == "200" ]] \
  && json_get "${HTTP_BODY}" "data.get('code') == 200" \
  && json_get "${HTTP_BODY}" "data.get('data', {}).get('app') == 'ok'" \
  && json_get "${HTTP_BODY}" "data.get('data', {}).get('postgres') == 'ok'" \
  && json_get "${HTTP_BODY}" "data.get('data', {}).get('redis') == 'ok'"; then
  pass_case "GET /healthz 三依赖正常"
else
  fail_case "GET /healthz 三依赖正常" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 3. 无 Token
request POST "/chat" \
  -H "Content-Type: application/json" \
  -d "$(chat_json '你好')"
if [[ "${HTTP_CODE}" == "401" ]] && json_get "${HTTP_BODY}" "data.get('code') == 401"; then
  pass_case "POST /chat 无 Token 返回 401"
else
  fail_case "POST /chat 无 Token 返回 401" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 4. 错误 Token
request POST "/chat" \
  -H "Authorization: Bearer wrong_token" \
  -H "Content-Type: application/json" \
  -d "$(chat_json '你好')"
if [[ "${HTTP_CODE}" == "401" ]]; then
  pass_case "POST /chat 错误 Token 返回 401"
else
  fail_case "POST /chat 错误 Token 返回 401" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 5. 空消息
request POST "/chat" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(chat_json '   ')"
if [[ "${HTTP_CODE}" == "400" ]]; then
  pass_case "POST /chat 空消息返回 400"
else
  fail_case "POST /chat 空消息返回 400" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 6. 超长消息
LONG_MSG="$(python3 -c "print('a' * 201)")"
request POST "/chat" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(chat_json "${LONG_MSG}")"
if [[ "${HTTP_CODE}" == "400" ]]; then
  pass_case "POST /chat 超长消息返回 400"
else
  fail_case "POST /chat 超长消息返回 400" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 7. 敏感词
request POST "/chat" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$(chat_json '请问尼玛是什么意思')"
if [[ "${HTTP_CODE}" == "400" ]] && json_get "${HTTP_BODY}" "'违规' in data.get('message', '')"; then
  pass_case "POST /chat 敏感词被拦截"
else
  fail_case "POST /chat 敏感词被拦截" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 8. 正常聊天（首次，cache miss）
if [[ "${SKIP_LLM}" == "1" ]]; then
  skip_case "POST /chat 首次提问成功" "SKIP_LLM=1"
else
  request POST "/chat" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(chat_json "${UNIQUE_MSG}")"
  if [[ "${HTTP_CODE}" == "200" ]] \
    && json_get "${HTTP_BODY}" "data.get('llm_reply')" \
    && json_get "${HTTP_BODY}" "data.get('from_cache') is False"; then
    pass_case "POST /chat 首次提问成功（cache miss）"
    CHAT_FIRST_OK=1
  else
    fail_case "POST /chat 首次提问成功（cache miss）" "status=${HTTP_CODE} body=${HTTP_BODY}"
  fi
fi

# 9. 缓存命中（相同消息第二次）
if [[ "${SKIP_LLM}" == "1" ]]; then
  skip_case "POST /chat 缓存命中" "SKIP_LLM=1"
elif [[ "${CHAT_FIRST_OK}" -ne 1 ]]; then
  skip_case "POST /chat 缓存命中" "首次提问未通过"
else
  request POST "/chat" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$(chat_json "${UNIQUE_MSG}")"
  if [[ "${HTTP_CODE}" == "200" ]] && json_get "${HTTP_BODY}" "data.get('from_cache') is True"; then
    pass_case "POST /chat 缓存命中（cache hit）"
  else
    fail_case "POST /chat 缓存命中（cache hit）" "status=${HTTP_CODE} body=${HTTP_BODY}"
  fi
fi

# 10. 历史分页
request GET "/history?user_id=${USER_ID}&page=1&page_size=10" \
  -H "Authorization: Bearer ${API_TOKEN}"
if [[ "${HTTP_CODE}" == "200" ]] \
  && json_get "${HTTP_BODY}" "data.get('code') == 200" \
  && json_get "${HTTP_BODY}" "'items' in data.get('data', {})"; then
  pass_case "GET /history 分页查询成功"
else
  fail_case "GET /history 分页查询成功" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 11. 历史无鉴权
request GET "/history?user_id=${USER_ID}&page=1&page_size=10"
if [[ "${HTTP_CODE}" == "401" ]]; then
  pass_case "GET /history 无 Token 返回 401"
else
  fail_case "GET /history 无 Token 返回 401" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

# 12. 非法分页参数
request GET "/history?user_id=${USER_ID}&page=0&page_size=10" \
  -H "Authorization: Bearer ${API_TOKEN}"
if [[ "${HTTP_CODE}" == "400" || "${HTTP_CODE}" == "422" ]]; then
  pass_case "GET /history 非法 page 被拒绝"
else
  fail_case "GET /history 非法 page 被拒绝" "status=${HTTP_CODE} body=${HTTP_BODY}"
fi

echo "----------------------------------------"
echo -e "结果: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}, ${YELLOW}${SKIP} skipped${NC}"
echo "----------------------------------------"

if [[ "${FAIL}" -gt 0 ]]; then
  exit 1
fi
exit 0
