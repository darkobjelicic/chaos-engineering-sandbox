#!/usr/bin/env bash
set -euo pipefail

GATEWAY_URL="http://localhost:8000"
EMAIL="e2e_test@example.com"
PASSWORD="secretpass"
NAME="E2E Test"

echo "1) Registering user: $EMAIL"
REG_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\", \"name\": \"$NAME\"}")

REG_BODY=$(echo "$REG_RES" | sed -n '1,$p' | sed '$d')
REG_STATUS=$(echo "$REG_RES" | tail -n1)
echo "Register status: $REG_STATUS"
echo "Body: $REG_BODY"

echo
echo "2) Logging in"
LOGIN_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/auth/login" \
  -d "username=$EMAIL&password=$PASSWORD")

LOGIN_BODY=$(echo "$LOGIN_RES" | sed -n '1,$p' | sed '$d')
LOGIN_STATUS=$(echo "$LOGIN_RES" | tail -n1)
echo "Login status: $LOGIN_STATUS"
echo "Body: $LOGIN_BODY"

TOKEN=$(echo "$LOGIN_BODY" | sed -n 's/.*"access_token"\s*:\s*"\([^"]*\)".*/\1/p')
if [ -z "$TOKEN" ]; then
  echo "Failed to extract token from login response" >&2
  exit 2
fi

echo
# Get current user info to include required user_id in OrderCreate
echo "3) Fetching current user via /auth/me"
ME_RES=$(curl -s -w "\n%{http_code}" -X GET "$GATEWAY_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN")
ME_BODY=$(echo "$ME_RES" | sed -n '1,$p' | sed '$d')
ME_STATUS=$(echo "$ME_RES" | tail -n1)
echo "Me status: $ME_STATUS"
echo "Body: $ME_BODY"
USER_ID=$(echo "$ME_BODY" | sed -n 's/.*"id"\s*:\s*\([0-9]*\).*/\1/p')
if [ -z "$USER_ID" ]; then
  echo "Failed to extract user id from /auth/me" >&2
  exit 3
fi

echo
echo "4) Creating order via gateway (Authorization: Bearer <token>)"
CREATE_RES=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL/orders" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"book_id": 1, "quantity": 1}')

CREATE_BODY=$(echo "$CREATE_RES" | sed -n '1,$p' | sed '$d')
CREATE_STATUS=$(echo "$CREATE_RES" | tail -n1)
echo "Create order status: $CREATE_STATUS"
echo "Body: $CREATE_BODY"

echo
echo "Done. If successful, consumers should have processed the order and logged events." 
