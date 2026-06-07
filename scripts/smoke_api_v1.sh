#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${FOOTLUMEN_API_BASE_URL:-http://127.0.0.1:8000}"
TOKEN_VALUE="${FOOTLUMEN_API_TOKEN:-}"

if [[ -z "$TOKEN_VALUE" ]]; then
  echo "ERROR: FOOTLUMEN_API_TOKEN must be set for smoke testing." >&2
  exit 2
fi

request_with_token() {
  local path="$1"
  curl -fsS \
    -H "Authorization: Bearer ${TOKEN_VALUE}" \
    "${BASE_URL}${path}" >/dev/null
  echo "OK ${path}"
}

request_expect_401_without_token() {
  local path="$1"
  local status
  status="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}${path}")"
  if [[ "$status" != "401" ]]; then
    echo "ERROR: expected 401 without token for ${path}, got ${status}" >&2
    exit 1
  fi
  echo "OK ${path} without token => 401"
}

request_with_token "/api/v1/health"
request_with_token "/api/v1/version"
request_with_token "/api/v1/competitions"
request_with_token "/api/v1/fixtures/today"
request_expect_401_without_token "/api/v1/health"

echo "API V1 smoke passed for ${BASE_URL}"
